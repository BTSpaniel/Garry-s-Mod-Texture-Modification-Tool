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
        
    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if updates are available from GitHub.
        
        Returns:
            Tuple containing:
            - Boolean indicating if update is available
            - Latest version string (if available)
            - Update notes (if available)
        """
        # Don't check too frequently
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return False, None, None
            
        self.last_check_time = current_time
        
        if not self.update_config.get("enabled", True):
            logging.info("Auto-updates are disabled")
            return False, None, None
            
        try:
            # Get latest release info from GitHub API
            logging.info("Checking for updates...")
            
            # Use GitHub API to get latest release
            request = urllib.request.Request(
                f"{self.api_url}/releases/latest",
                headers={"User-Agent": "Source-Engine-Asset-Manager-Updater"}
            )
            
            with urllib.request.urlopen(request, timeout=10) as response:
                release_data = json.loads(response.read().decode('utf-8'))
            
            # Extract version from tag name
            tag_name = release_data.get("tag_name", "")
            # Try to find a version pattern like v1.2.3 or 1.2.3
            import re
            version_match = re.search(r'v?(\d+\.\d+\.\d+)', tag_name)
            if version_match:
                latest_version = version_match.group(1)
            else:
                latest_version = tag_name.lstrip("v")
                
            release_notes = release_data.get("body", "No release notes available")
            
            # Compare versions
            if self._is_newer_version(latest_version):
                logging.info(f"Update available: {latest_version} (current: {self.current_version})")
                return True, latest_version, release_notes
            else:
                logging.info(f"No updates available. Current version: {self.current_version}")
                return False, None, None
                
        except Exception as e:
            logging.warning(f"Failed to check for updates: {e}")
            return False, None, None
    
    def download_update(self, version: str) -> bool:
        """
        Download the specified version update from GitHub.
        
        Args:
            version: Version to download
            
        Returns:
            Boolean indicating success
        """
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
            return True
            
        except Exception as e:
            logging.error(f"Failed to download update: {e}")
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
                logging.error("No directories found in extracted update")
                self._cleanup()
                self.update_in_progress = False
                return False
                
            source_dir = extracted_dirs[0]
            
            # Create backup of current version
            backup_dir = self.app_dir.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logging.info(f"Creating backup at: {backup_dir}")
            shutil.copytree(self.app_dir, backup_dir, ignore=shutil.ignore_patterns(
                '__pycache__', '*.pyc', '*.pyo', '*.pyd', 'logs', 'temp', 'extracted', '.git'
            ))
            
            # Copy new files, preserving user data
            self._copy_update_files(source_dir, self.app_dir)
            
            # Update version in config
            self._update_version_info(version)
            
            logging.info(f"Update to version {version} completed successfully")
            
            # Clean up
            self._cleanup()
            self.update_in_progress = False
            return True
            
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
            
            logging.debug(f"Comparing versions: current={current_parts}, latest={latest_parts}")
            
            # Compare version components
            for i in range(3):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False
                    
            # If we get here, versions are equal
            return False
            
        except Exception as e:
            logging.warning(f"Error comparing versions: {e}")
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
            'custom/*'
        ]
        
        # Copy all files except those matching preserve patterns
        for src_path in source_dir.glob('**/*'):
            if src_path.is_file():
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
                
                # Copy file
                shutil.copy2(src_path, dst_path)
                logging.debug(f"Updated file: {rel_path}")
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching for file paths."""
        if pattern.endswith('/*'):
            return path.startswith(pattern[:-1])
        return path == pattern
    
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
    
    def restart_application(self):
        """Restart the application to apply updates."""
        try:
            logging.info("Restarting application...")
            
            # Get the path to the Python executable and script
            python = sys.executable
            script = sys.argv[0]
            
            # Close logs
            logging.shutdown()
            
            # Restart the application
            os.execl(python, python, script)
            
        except Exception as e:
            logging.error(f"Failed to restart application: {e}")
