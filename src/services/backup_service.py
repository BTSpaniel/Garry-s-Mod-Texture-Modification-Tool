"""
Backup Service for Texture Extractor
Handles backup creation and management
"""

import os
import logging
import shutil
import zipfile
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

class BackupService:
    """Service for creating and managing backups."""
    
    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config
        self.backup_config = config.get("BACKUP", {})
    
    def create_backup(self, path: Path) -> Optional[str]:
        """Create a backup of the specified path with enhanced options."""
        if not self.backup_config.get("enabled", False):
            logging.info("Backup creation is disabled")
            return None
    
        backup_path = None
        try:
            # Create backup location
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_location = Path(self.backup_config.get("location") or os.path.expanduser("~/Desktop/texture_backups"))
            backup_path = backup_location / f"backup_{timestamp}"
            
            # Create backup directory if it doesn't exist
            os.makedirs(backup_location, exist_ok=True)
            
            # Create backup based on format
            if self.backup_config.get("compression", True):
                backup_path = backup_path.with_suffix('.zip')
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in path.rglob('*'):
                        if file.is_file() and self.should_backup_file(file):
                            try:
                                rel_path = file.relative_to(path)
                                zipf.write(file, rel_path)
                                logging.debug(f"Backed up: {rel_path}")
                            except Exception as e:
                                logging.warning(f"Failed to backup file {file}: {e}")
            else:
                backup_dir = backup_path.with_suffix('')
                for file in path.rglob('*'):
                    if file.is_file() and self.should_backup_file(file):
                        try:
                            rel_path = file.relative_to(path)
                            target = backup_dir / rel_path
                            os.makedirs(target.parent, exist_ok=True)
                            shutil.copy2(file, target)
                            logging.debug(f"Backed up: {rel_path}")
                        except Exception as e:
                            logging.warning(f"Failed to backup file {file}: {e}")
            
            logging.info(f"Created backup at: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            if backup_path and backup_path.exists():
                try:
                    backup_path.unlink()
                except Exception as cleanup_error:
                    logging.warning(f"Failed to clean up failed backup: {cleanup_error}")
            return None
    
    def should_backup_file(self, file_path: Path) -> bool:
        """Determine if a file should be included in backup based on settings."""
        if not self.backup_config.get("enabled", False):
            return False
            
        # Check file extension
        ext = file_path.suffix.lower()
        
        # Always backup VMT and VTF files
        if ext in ['.vmt', '.vtf']:
            return True
            
        # Backup config files if enabled
        if self.backup_config.get("include_cfg", True) and ext == '.cfg':
            return True
            
        # Backup material files if enabled
        if self.backup_config.get("include_materials", True) and 'materials' in str(file_path):
            return True
            
        return False
    
    def verify_backup(self, backup_path: Path, manifest: Dict) -> bool:
        """Verify backup integrity."""
        try:
            if self.backup_config.get("compression", True):
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    # Check file list matches manifest
                    zip_files = set(zipf.namelist())
                    manifest_files = set(manifest['files'])
                    if zip_files != manifest_files:
                        logging.error("Backup file list mismatch")
                        return False
                    return True
            else:
                # Verify directory backup
                backup_dir = backup_path.with_suffix('')
                for file_path in manifest['files']:
                    if not (backup_dir / file_path).exists():
                        logging.error(f"Missing file in backup: {file_path}")
                        return False
                return True
        except Exception as e:
            logging.error(f"Backup verification failed: {e}")
            return False
    
    def clean_old_backups(self) -> None:
        """Remove old backups to keep only the specified number."""
        try:
            max_backups = self.backup_config.get("max_backups", 5)
            backup_location = Path(self.backup_config.get("location") or os.path.expanduser("~/Desktop/texture_backups"))
            
            if not backup_location.exists():
                return
            
            # Get all backups sorted by creation time
            backups = []
            for ext in ['.zip', '']:
                pattern = f"backup_*{ext}"
                backups.extend(backup_location.glob(pattern))
            
            # Sort backups by creation time (oldest first)
            backups.sort(key=lambda p: p.stat().st_ctime)
            
            # Remove oldest backups if we have too many
            while len(backups) > max_backups:
                try:
                    oldest = backups.pop(0)
                    if oldest.is_dir():
                        shutil.rmtree(oldest)
                    else:
                        oldest.unlink()
                    logging.info(f"Removed old backup: {oldest}")
                except Exception as e:
                    logging.warning(f"Failed to remove old backup {oldest}: {e}")
        except Exception as e:
            logging.error(f"Error cleaning old backups: {e}")
    
    def create_backup_manifest(self, backup_path: Path, files: List[Path]) -> bool:
        """Create a manifest file for the backup."""
        try:
            manifest = {
                'timestamp': datetime.now().isoformat(),
                'backup_path': str(backup_path),
                'files': [str(f) for f in files],
                'file_count': len(files)
            }
            
            manifest_path = backup_path.with_suffix('.manifest.json')
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
                
            return True
        except Exception as e:
            logging.error(f"Failed to create backup manifest: {e}")
            return False
