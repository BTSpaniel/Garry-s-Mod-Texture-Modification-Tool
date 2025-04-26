"""
Update Service for Source Engine Asset Manager
Handles automatic updates from GitHub repository
"""

import os
import sys
import logging
import tempfile
import shutil
import subprocess
import json
import time
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import urllib.request
import urllib.error

class UpdateService:
    """Service for checking and applying updates from GitHub."""
    
    def __init__(self, config: Dict = None):
        """Initialize with configuration."""
        self.config = config or {}
        self.update_config = self.config.get("UPDATE", {})
        self.repo_url = "https://github.com/BTSpaniel/Garry-s-Mod-Texture-Modification-Tool"
        self.api_url = "https://api.github.com/repos/BTSpaniel/Garry-s-Mod-Texture-Modification-Tool"
        
        # Get current version from config or main module
        self.current_version = self.config.get("VERSION", "0.0.0")
        
        # If version is still 0.0.0, try to get it from main.py
        if self.current_version == "0.0.0":
            try:
                # Get the path to main.py
                main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'main.py')
                
                # Read main.py to extract VERSION
                with open(main_path, 'r') as f:
                    content = f.read()
                    import re
                    version_match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
                    if version_match:
                        self.current_version = version_match.group(1)
                        logging.info(f"Found version in main.py: {self.current_version}")
            except Exception as e:
                logging.warning(f"Failed to get version from main.py: {e}")
        
        self.app_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.temp_dir = None
        self.update_in_progress = False
        self.last_check_time = 0
        self.check_interval = self.update_config.get("check_interval", 86400)  # Default: once per day
        
        # Check for post-update tasks from previous update
        self._check_for_post_update_tasks()
        
    def check_for_updates(self, force_check=False, force_update=False) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if updates are available from GitHub.
        
        Args:
            force_check: If True, bypass the time interval check and force a fresh check
            force_update: If True, return an update is available even if versions match
        
        Returns:
            Tuple containing:
            - Boolean indicating if update is available
            - Latest version string (if available)
            - Update notes (if available)
        """
        # Don't check too frequently unless forced
        current_time = time.time()
        if not force_check and current_time - self.last_check_time < self.check_interval:
            logging.debug(f"Skipping update check due to time interval (last check: {int(current_time - self.last_check_time)} seconds ago)")
            return False, None, None
            
        self.last_check_time = current_time
        
        if not self.update_config.get("enabled", True) and not force_check:
            logging.info("Auto-updates are disabled")
            return False, None, None
            
        try:
            # Get latest release info from GitHub API
            logging.info("Checking for updates from GitHub...")
            
            # Use GitHub API to get latest release with cache-busting
            headers = {
                "User-Agent": "Source-Engine-Asset-Manager-Updater",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            
            # Add a cache-busting parameter to the URL
            cache_buster = f"?t={int(time.time())}"
            request = urllib.request.Request(
                f"{self.api_url}/releases/latest{cache_buster}",
                headers=headers
            )
            
            with urllib.request.urlopen(request, timeout=15) as response:
                release_data = json.loads(response.read().decode('utf-8'))
            
            # Get release notes before we potentially download the zip
            release_notes = release_data.get("body", "No release notes available")
            
            # First, try to extract version from GitHub API response
            tag_name = release_data.get("tag_name", "")
            logging.info(f"Latest GitHub release tag: {tag_name}")
            
            # Create a temporary directory for downloading the zip
            temp_dir = Path(tempfile.mkdtemp())
            zip_path = temp_dir / "update.zip"
            
            # Get the download URL from the release assets or fallback to archive URL
            download_url = None
            assets = release_data.get("assets", [])
            for asset in assets:
                if asset.get("name", "").endswith(".zip"):
                    download_url = asset.get("browser_download_url")
                    break
            
            # If no asset found, use the source code zip URL
            if not download_url:
                download_url = release_data.get("zipball_url")
                
            # If still no URL, construct one based on tag name or default to main branch
            if not download_url:
                if tag_name:
                    download_url = f"{self.repo_url}/archive/refs/tags/{tag_name}.zip"
                else:
                    download_url = f"{self.repo_url}/archive/refs/heads/main.zip"
            
            logging.info(f"Downloading update zip from: {download_url}")
            
            # Download the zip file
            try:
                urllib.request.urlretrieve(
                    download_url, 
                    zip_path,
                    reporthook=self._download_progress
                )
                logging.info("Download complete for version check")
            except Exception as e:
                logging.error(f"Failed to download update zip for version check: {e}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, None, None
            
            # Extract version from the downloaded zip
            latest_version = self._extract_version_from_zip(zip_path)
            
            # If we couldn't extract a version from the zip, try the GitHub API response
            if not latest_version:
                import re
                # Try tag name first
                version_match = re.search(r'v?(\d+\.\d+\.\d+)', tag_name)
                if version_match:
                    latest_version = version_match.group(1)
                else:
                    # Look for numbers in the tag name
                    version_match = re.search(r'(\d+)[\.-]?(\d+)[\.-]?(\d+)', tag_name)
                    if version_match:
                        # Format as proper version number
                        latest_version = f"{version_match.group(1)}.{version_match.group(2)}.{version_match.group(3)}"
                        logging.info(f"Extracted version from tag numbers: {latest_version}")
                    else:
                        # Try release name
                        release_name = release_data.get("name", "")
                        version_match = re.search(r'v?(\d+\.\d+\.\d+)', release_name)
                        if version_match:
                            latest_version = version_match.group(1)
                        else:
                            # Try to extract numbers from release name
                            version_match = re.search(r'(\d+)[\.-]?(\d+)[\.-]?(\d+)', release_name)
                            if version_match:
                                latest_version = f"{version_match.group(1)}.{version_match.group(2)}.{version_match.group(3)}"
                                logging.info(f"Extracted version from release name numbers: {latest_version}")
                            else:
                                # Try release body
                                version_match = re.search(r'[vV]ersion\s*:?\s*v?(\d+\.\d+\.\d+)', release_notes)
                                if version_match:
                                    latest_version = version_match.group(1)
                                else:
                                    # Fallback to current version to prevent false update notifications
                                    latest_version = self.current_version
                                    logging.warning(f"Could not extract version from any source, using current version: {latest_version}")
            
            # Save the zip file for later use if we need to apply the update
            if not self.temp_dir:
                self.temp_dir = temp_dir
            else:
                # Copy the zip to our existing temp dir and clean up the temporary one
                shutil.copy2(zip_path, self.temp_dir / "update.zip")
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            logging.info(f"Using latest version for comparison: {latest_version}")
            logging.info(f"Current version: {self.current_version}")
            
            # Compare versions
            is_newer = self._is_newer_version(latest_version)
            logging.info(f"Is {latest_version} newer than {self.current_version}? {is_newer}")
            
            # If force_update is True, we'll consider it an update even if versions match
            if force_update and latest_version == self.current_version:
                logging.info(f"Forcing update even though versions match: {latest_version}")
                is_newer = True
            
            if is_newer:
                logging.info(f"Update available: {latest_version} (current: {self.current_version})")
                self.update_in_progress = True  # Mark that we've already downloaded the update
                return True, latest_version, release_notes
            else:
                logging.info(f"No updates available. Current version: {self.current_version}, Latest: {latest_version}")
                # Clean up the temp dir since we won't be using it
                self._cleanup()
                return False, None, None
                
        except urllib.error.URLError as ue:
            logging.warning(f"Network error checking for updates: {ue}")
            return False, None, None
        except Exception as e:
            logging.warning(f"Failed to check for updates: {e}")
            import traceback
            logging.debug(traceback.format_exc())
            return False, None, None
    
    def download_update(self, version: str) -> bool:
        """
        Download the specified version update from GitHub.
        
        Args:
            version: Version to download
            
        Returns:
            Boolean indicating success
        """
        # If we already have the update zip from the check_for_updates call,
        # we can skip the download and just verify the file
        if self.update_in_progress and self.temp_dir and (self.temp_dir / "update.zip").exists():
            logging.info("Update zip already downloaded during version check")
            zip_path = self.temp_dir / "update.zip"
            
            # Verify the downloaded file
            if not self._verify_update_file(zip_path, version):
                logging.error("Downloaded update file verification failed")
                self._cleanup()
                self.update_in_progress = False
                return False
                
            logging.info("Update file verified successfully")
            return True
            
        # Otherwise, proceed with normal download
        if self.update_in_progress and not self.temp_dir:
            logging.warning("Update marked as in progress but no temp directory exists")
            self.update_in_progress = False
            
        if self.update_in_progress:
            logging.warning("Update already in progress")
            return False
            
        self.update_in_progress = True
        
        try:
            # Create temp directory
            self.temp_dir = Path(tempfile.mkdtemp())
            zip_path = self.temp_dir / "update.zip"
            
            # Try to download from tag first, fall back to main branch if that fails
            try:
                # Try to download from tag
                download_url = f"{self.repo_url}/archive/refs/tags/v{version}.zip"
                logging.info(f"Attempting to download update from tag: {download_url}")
                
                # Download with progress reporting
                urllib.request.urlretrieve(
                    download_url, 
                    zip_path,
                    reporthook=self._download_progress
                )
            except urllib.error.HTTPError as e:
                if e.code == 404:  # Tag not found
                    logging.info(f"Tag v{version} not found, falling back to main branch")
                    # Fall back to main branch
                    download_url = f"{self.repo_url}/archive/refs/heads/main.zip"
                    logging.info(f"Downloading update from main branch: {download_url}")
                    
                    # Download with progress reporting
                    urllib.request.urlretrieve(
                        download_url, 
                        zip_path,
                        reporthook=self._download_progress
                    )
                else:
                    raise  # Re-raise if it's not a 404 error
            
            logging.info("Download complete")
            
            # Verify the downloaded file
            if not self._verify_update_file(zip_path, version):
                logging.error("Downloaded update file verification failed")
                self._cleanup()
                self.update_in_progress = False
                return False
                
            logging.info("Update file verified successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to download update: {e}")
            import traceback
            logging.debug(traceback.format_exc())
            self._cleanup()
            self.update_in_progress = False
            return False
    
    def apply_update(self, version: str) -> bool:
        """
        Apply the downloaded update.
        
        Args:
            version: Version to apply
            
        Returns:
            Boolean indicating success
        """
        if not self.temp_dir or not self.update_in_progress:
            logging.error("No update downloaded to apply")
            return False
            
        try:
            zip_path = self.temp_dir / "update.zip"
            extract_dir = self.temp_dir / "extracted"
            os.makedirs(extract_dir, exist_ok=True)
            
            # Extract zip file
            logging.info("Extracting update...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the extracted directory (usually has the repo name and version)
            extracted_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                # Try looking for files directly in the extract_dir
                if any(f for f in extract_dir.iterdir() if f.is_file() and f.name != 'update.zip'):
                    source_dir = extract_dir
                    logging.info("Using root of extracted zip as source directory")
                else:
                    logging.error("No directories or files found in extracted update")
                    self._cleanup()
                    self.update_in_progress = False
                    return False
            else:
                source_dir = extracted_dirs[0]
                logging.info(f"Using {source_dir.name} as source directory")
            
            # Create backup of current version
            backup_enabled = self.update_config.get('backup_before_update', True)
            if backup_enabled:
                backup_dir = self.app_dir.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logging.info(f"Creating backup at: {backup_dir}")
                try:
                    shutil.copytree(self.app_dir, backup_dir, ignore=shutil.ignore_patterns(
                        '__pycache__', '*.pyc', '*.pyo', '*.pyd', 'logs', 'temp', 'extracted', '.git'
                    ))
                    logging.info("Backup created successfully")
                except Exception as backup_error:
                    logging.error(f"Failed to create backup: {backup_error}")
                    # Continue with update even if backup fails
            else:
                logging.info("Backup before update is disabled")
            
            # Copy new files, preserving user data
            logging.info(f"Copying files from {source_dir} to {self.app_dir}")
            self._copy_update_files(source_dir, self.app_dir)
            
            # Update version in config
            self._update_version_info(version)
            
            # Save the current version to a file that will persist across restarts
            version_file = self.app_dir / ".version"
            try:
                with open(version_file, 'w') as f:
                    f.write(version)
                logging.info(f"Saved version {version} to {version_file}")
            except Exception as ve:
                logging.warning(f"Could not save version file: {ve}")
            
            logging.info(f"Update to version {version} completed successfully")
            
            # Don't clean up yet - we need the temp dir for restart script
            # We'll clean up on next start
            self.update_in_progress = False
            return True
            
        except PermissionError as pe:
            logging.error(f"Permission error applying update: {pe}")
            logging.info("This may be due to files being locked by the running application")
            self.update_in_progress = False
            return False
        except Exception as e:
            logging.error(f"Failed to apply update: {e}")
            self._cleanup()
            self.update_in_progress = False
            return False
    
    def _is_newer_version(self, latest_version: str) -> bool:
        """Check if latest version is newer than current version."""
        try:
            # Extract numeric version parts using regex
            import re
            
            # Function to safely extract version components
            def extract_version_parts(version_str):
                # Try to find a version pattern like 1.2.3
                match = re.search(r'(\d+)(?:\.(\d+))?(?:\.(\d+))?', version_str)
                if not match:
                    logging.warning(f"Could not parse version: {version_str}")
                    return [0, 0, 0]  # Default if no version found
                
                # Extract the parts, defaulting to 0 if not present
                parts = []
                for i in range(1, 4):
                    try:
                        part = match.group(i)
                        parts.append(int(part) if part else 0)
                    except (IndexError, TypeError):
                        parts.append(0)
                return parts
            
            # Extract version parts
            current_parts = extract_version_parts(self.current_version)
            latest_parts = extract_version_parts(latest_version)
            
            # Log the parsed version components for debugging
            logging.info(f"Comparing versions: current={current_parts}, latest={latest_parts}")
            
            # Compare version components
            for i in range(3):
                if latest_parts[i] > current_parts[i]:
                    logging.info(f"Latest version {latest_version} is newer than current version {self.current_version}")
                    return True
                elif latest_parts[i] < current_parts[i]:
                    logging.info(f"Latest version {latest_version} is older than current version {self.current_version}")
                    return False
            
            # Special case: If GitHub has a different version with the same numbers
            # (e.g., a re-release with fixes but same version number)
            # We can force an update by checking if the versions are exactly equal but have different string representations
            if latest_version != self.current_version and latest_parts == current_parts:
                logging.info(f"Versions have same numbers but different strings: {latest_version} vs {self.current_version}")
                # This is a special case where we might want to force an update
                # For now, we'll treat them as equal, but you could return True here to force an update
                
            # If we get here, versions are equal
            logging.info(f"Versions are equal: {latest_version} = {self.current_version}")
            return False
            
        except Exception as e:
            logging.warning(f"Error comparing versions: {e}")
            import traceback
            logging.debug(traceback.format_exc())
            # If there's an error parsing versions, assume no update needed
            return False
    
    def _download_progress(self, count, block_size, total_size):
        """Report download progress."""
        percent = int(count * block_size * 100 / total_size)
        sys.stdout.write(f"\rDownloading update: {percent}%")
        sys.stdout.flush()
    
    def _copy_update_files(self, source_dir: Path, target_dir: Path):
        """
        Copy update files, preserving user data.
        
        Args:
            source_dir: Source directory with new files
            target_dir: Target directory to update
        """
        # Files to preserve (don't overwrite)
        preserve_patterns = [
            'logs/*',
            'config.json',
            'user_settings.json',
            '.env',
            'custom/*',
            '.git/*',
            '.gitignore'
        ]
        
        # Files that might be locked by the running application
        potentially_locked_files = []
        
        # Copy all files except those matching preserve patterns
        for src_path in source_dir.glob('**/*'):
            if src_path.is_file():
                try:
                    # Get relative path
                    rel_path = src_path.relative_to(source_dir)
                    dst_path = target_dir / rel_path
                    
                    # Check if file should be preserved
                    should_preserve = False
                    for pattern in preserve_patterns:
                        if self._match_pattern(str(rel_path), pattern):
                            should_preserve = True
                            break
                    
                    # Skip if file should be preserved and exists
                    if should_preserve and dst_path.exists():
                        logging.info(f"Preserving user file: {rel_path}")
                        continue
                        
                    # Create parent directories if needed
                    os.makedirs(dst_path.parent, exist_ok=True)
                    
                    # Try to copy the file
                    try:
                        # First try to open the destination file to see if it's locked
                        if dst_path.exists():
                            try:
                                with open(dst_path, 'a+b') as test:
                                    pass  # Just testing if we can open it for writing
                            except PermissionError:
                                # File is locked, add to list to retry later
                                potentially_locked_files.append((src_path, dst_path))
                                logging.warning(f"File appears to be locked, will retry: {rel_path}")
                                continue
                        
                        # Copy file
                        shutil.copy2(src_path, dst_path)
                        logging.debug(f"Updated file: {rel_path}")
                    except PermissionError:
                        # File is locked, add to list to retry later
                        potentially_locked_files.append((src_path, dst_path))
                        logging.warning(f"Permission error copying file, will retry: {rel_path}")
                except Exception as e:
                    logging.error(f"Error copying file {src_path}: {e}")
        
        # If we have locked files, create a post-update script to copy them after restart
        if potentially_locked_files:
            logging.info(f"Found {len(potentially_locked_files)} locked files that will be updated after restart")
            try:
                # Create a script to copy these files after restart
                post_update_dir = self.temp_dir / "post_update"
                os.makedirs(post_update_dir, exist_ok=True)
                
                # Copy the locked files to the post_update directory
                for src_path, _ in potentially_locked_files:
                    rel_path = src_path.relative_to(source_dir)
                    post_update_file = post_update_dir / rel_path
                    os.makedirs(post_update_file.parent, exist_ok=True)
                    shutil.copy2(src_path, post_update_file)
                
                # Create a marker file with instructions
                with open(self.temp_dir / "post_update.json", 'w') as f:
                    import json
                    json.dump({
                        "source_dir": str(post_update_dir),
                        "target_dir": str(target_dir),
                        "files": [str(src.relative_to(source_dir)) for src, _ in potentially_locked_files]
                    }, f)
                
                logging.info(f"Created post-update script at {self.temp_dir / 'post_update.json'}")
            except Exception as e:
                logging.error(f"Error creating post-update script: {e}")
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching for file paths."""
        if pattern.endswith('/*'):
            return path.startswith(pattern[:-1])
        return path == pattern
        
    def _extract_version_from_zip(self, zip_path: Path) -> Optional[str]:
        """
        Extract the version number from main.py inside the ZIP file.
        
        Args:
            zip_path: Path to the downloaded zip file
            
        Returns:
            Extracted version string or None if not found
        """
        if not zip_path.exists():
            logging.error(f"ZIP file not found at {zip_path}")
            return None
            
        try:
            # Open the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the list of files in the zip
                file_list = zip_ref.namelist()
                
                # Look for main.py in the zip
                main_py_files = [f for f in file_list if f.endswith('main.py')]
                if not main_py_files:
                    logging.warning("No main.py found in the ZIP file")
                    return None
                    
                # Try each main.py file until we find a version
                for main_py in main_py_files:
                    try:
                        with zip_ref.open(main_py) as f:
                            content = f.read().decode('utf-8')
                            import re
                            version_match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
                            if version_match:
                                version = version_match.group(1)
                                logging.info(f"Found version {version} in {main_py} inside ZIP")
                                return version
                    except Exception as e:
                        logging.warning(f"Error reading {main_py} from ZIP: {e}")
                        continue
                
                logging.warning("Could not find VERSION in any main.py file in the ZIP")
                return None
                
        except zipfile.BadZipFile:
            logging.error("Downloaded file is not a valid ZIP archive")
            return None
        except Exception as e:
            logging.error(f"Error extracting version from ZIP: {e}")
            import traceback
            logging.debug(traceback.format_exc())
            return None
            
    def _verify_update_file(self, zip_path: Path, expected_version: str) -> bool:
        """
        Verify that the downloaded update file is valid and contains the expected content.
        
        Args:
            zip_path: Path to the downloaded zip file
            expected_version: The version we expect to find in the update
            
        Returns:
            Boolean indicating if the file is valid
        """
        if not zip_path.exists():
            logging.error(f"Update file not found at {zip_path}")
            return False
            
        # Check file size (should be at least 100KB for a valid update)
        file_size = zip_path.stat().st_size
        if file_size < 100 * 1024:  # 100KB
            logging.error(f"Update file too small: {file_size} bytes")
            return False
            
        logging.info(f"Update file size: {file_size / (1024*1024):.2f} MB")
        
        try:
            # Check if it's a valid zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the list of files in the zip
                file_list = zip_ref.namelist()
                
                if len(file_list) < 10:  # A valid update should have more than 10 files
                    logging.error(f"Update zip contains too few files: {len(file_list)}")
                    return False
                    
                logging.info(f"Update zip contains {len(file_list)} files")
                
                # Check for critical files that should be present in any valid update
                critical_files = [
                    "main.py",
                    "requirements.txt",
                    "src/services/update_service.py",
                    "src/gui/main_window.py"
                ]
                
                # The files might be in a subdirectory with the repo name
                # Find the root directory in the zip
                root_dirs = set()
                for file_path in file_list:
                    parts = file_path.split('/')
                    if len(parts) > 1:
                        root_dirs.add(parts[0])
                
                # Check if any root directory contains the critical files
                found_critical_files = False
                for root_dir in root_dirs:
                    if all(any(f.endswith(critical_file) for f in file_list) 
                           for critical_file in critical_files):
                        found_critical_files = True
                        break
                
                if not found_critical_files:
                    logging.error("Update zip does not contain critical application files")
                    return False
                
                # Try to find version information in the zip
                version_found = False
                for file_path in file_list:
                    if file_path.endswith('main.py'):
                        try:
                            with zip_ref.open(file_path) as f:
                                content = f.read().decode('utf-8')
                                import re
                                version_match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
                                if version_match:
                                    zip_version = version_match.group(1)
                                    logging.info(f"Found version in zip: {zip_version}")
                                    
                                    # Check if the version in the zip matches what we expect
                                    if zip_version == expected_version:
                                        version_found = True
                                        break
                                    else:
                                        logging.warning(f"Version mismatch: expected {expected_version}, found {zip_version}")
                        except Exception as e:
                            logging.warning(f"Error reading main.py from zip: {e}")
                
                # If we couldn't verify the version, we'll still accept the update if all other checks passed
                if not version_found:
                    logging.warning("Could not verify version in update zip, but file structure looks valid")
                
                return True
                
        except zipfile.BadZipFile:
            logging.error("Downloaded file is not a valid zip archive")
            return False
        except Exception as e:
            logging.error(f"Error verifying update file: {e}")
            import traceback
            logging.debug(traceback.format_exc())
            return False
    
    def _update_version_info(self, version: str):
        """Update version information in main.py."""
        try:
            main_py = self.app_dir / "main.py"
            if not main_py.exists():
                logging.warning("main.py not found, cannot update version")
                return
                
            # Read main.py
            with open(main_py, 'r') as f:
                content = f.read()
                
            # Update version
            import re
            new_content = re.sub(
                r'VERSION\s*=\s*"[^"]+"', 
                f'VERSION = "{version}"', 
                content
            )
            
            # Write updated content
            with open(main_py, 'w') as f:
                f.write(new_content)
                
            logging.info(f"Updated version in main.py to {version}")
            
        except Exception as e:
            logging.error(f"Failed to update version info: {e}")
    
    def _cleanup(self):
        """Clean up temporary files."""
        try:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
        except Exception as e:
            logging.warning(f"Failed to clean up temporary files: {e}")
            
    def _check_for_post_update_tasks(self):
        """Check for and complete any post-update tasks from previous update."""
        try:
            # Look for temporary directories in the system temp folder
            temp_base = Path(tempfile.gettempdir())
            post_update_files = list(temp_base.glob("**/post_update.json"))
            
            # Also check the app directory for any post_update.json files
            app_post_update = list(self.app_dir.glob("**/post_update.json"))
            post_update_files.extend(app_post_update)
            
            if not post_update_files:
                return
                
            logging.info(f"Found {len(post_update_files)} post-update tasks to complete")
            
            for post_update_file in post_update_files:
                try:
                    # Load the post-update instructions
                    with open(post_update_file, 'r') as f:
                        import json
                        instructions = json.load(f)
                    
                    source_dir = Path(instructions.get("source_dir"))
                    target_dir = Path(instructions.get("target_dir"))
                    files = instructions.get("files", [])
                    
                    if not source_dir.exists() or not target_dir.exists() or not files:
                        logging.warning(f"Invalid post-update instructions in {post_update_file}")
                        continue
                    
                    logging.info(f"Applying {len(files)} pending file updates from previous update")
                    
                    # Copy each file
                    success_count = 0
                    for rel_path in files:
                        try:
                            src_path = source_dir / rel_path
                            dst_path = target_dir / rel_path
                            
                            if not src_path.exists():
                                logging.warning(f"Source file not found: {src_path}")
                                continue
                                
                            # Create parent directories if needed
                            os.makedirs(dst_path.parent, exist_ok=True)
                            
                            # Copy the file
                            shutil.copy2(src_path, dst_path)
                            success_count += 1
                            logging.debug(f"Applied pending update to: {rel_path}")
                        except Exception as file_error:
                            logging.error(f"Error applying pending update to {rel_path}: {file_error}")
                    
                    logging.info(f"Successfully applied {success_count} of {len(files)} pending file updates")
                    
                    # Delete the post-update file and directory
                    try:
                        if source_dir.exists():
                            shutil.rmtree(source_dir)
                        post_update_file.unlink()
                        logging.info(f"Cleaned up post-update files")
                    except Exception as cleanup_error:
                        logging.warning(f"Error cleaning up post-update files: {cleanup_error}")
                        
                except Exception as task_error:
                    logging.error(f"Error processing post-update task {post_update_file}: {task_error}")
        except Exception as e:
            logging.error(f"Error checking for post-update tasks: {e}")
    
    def restart_application(self):
        """Restart the application to apply updates."""
        try:
            logging.info("Restarting application...")
            
            # Get the path to the Python executable and script
            python = sys.executable
            script = os.path.abspath(sys.argv[0])
            script_dir = os.path.dirname(script)
            
            # Get command line arguments
            args = sys.argv[1:]
            args_str = ' '.join(f'"{arg}"' for arg in args) if args else ''
            
            # Create a unique marker file to verify restart success
            marker_file = Path(tempfile.gettempdir()) / f"texture_extractor_restart_{int(time.time())}.marker"
            with open(marker_file, 'w') as f:
                f.write(f"Restart marker created at {datetime.now().isoformat()}\n")
            
            logging.info(f"Created restart marker: {marker_file}")
            
            # Close logs
            logging.shutdown()
            
            # On Windows, use a different approach for restarting
            if sys.platform.startswith('win'):
                # Create a batch file to restart the application after a short delay
                restart_script = self.temp_dir / "restart.bat" if self.temp_dir else Path(tempfile.gettempdir()) / "restart.bat"
                
                with open(restart_script, 'w') as f:
                    f.write(f"@echo off\n")
                    f.write(f"cd /d \"{script_dir}\"\n")  # Change to the script directory
                    f.write(f"echo Waiting for application to close...\n")
                    f.write(f"timeout /t 2 /nobreak > nul\n")  # Wait 2 seconds
                    f.write(f"echo Starting application...\n")
                    # Use the full path to the script and preserve command line arguments
                    f.write(f"start \"Texture Extractor\" \"{python}\" \"{script}\" {args_str}\n")
                    # Delete the marker file to indicate successful restart
                    f.write(f"if exist \"{marker_file}\" del \"{marker_file}\"\n")
                    # Self-delete the batch file
                    f.write(f"(goto) 2>nul & del \"%~f0\"\n")
                
                # Execute the batch file and exit current process
                logging.info(f"Executing restart script: {restart_script}")
                # Use CREATE_NEW_CONSOLE flag to ensure the batch file runs in a new console
                subprocess.Popen([str(restart_script)], 
                               shell=True, 
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
                
                # Exit the current process
                sys.exit(0)
            else:
                # On other platforms, use execl
                os.execl(python, python, script, *args)
            
        except Exception as e:
            logging.error(f"Failed to restart application: {e}")
