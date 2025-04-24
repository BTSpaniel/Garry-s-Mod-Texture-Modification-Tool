"""
File Processor Service for Texture Extractor
Handles processing of VPK, BSP, and GMA files
"""

import os
import struct
import logging
import vpk
from pathlib import Path
from typing import List, Optional, Tuple

class FileProcessor:
    """Service for processing game files to extract textures and sounds."""
    
    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config
        self.c4_sound_paths = []
    
    def process_file(self, file_path: Path) -> List[str]:
        """Process a file based on its extension."""
        try:
            ext = file_path.suffix.lower()
            
            if ext == '.vpk':
                return self.process_vpk_file(file_path)
            elif ext == '.bsp':
                return self.process_bsp_file(file_path)
            elif ext == '.gma':
                return self.process_gma_file(file_path)
            else:
                logging.warning(f"Unsupported file type: {file_path}")
                return []
                
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")
            return []
    
    def process_vpk_file(self, file_path: Path) -> List[str]:
        """Process a VPK file and extract texture and sound information."""
        try:
            if not file_path.exists():
                logging.error(f"File not found: {file_path}")
                return []
                
            # Only process _dir.vpk files, skip numbered VPK files
            if not file_path.name.endswith('_dir.vpk'):
                logging.debug(f"Skipping non-directory VPK file: {file_path}")
                return []
                
            # Initialize VPK package with error handling
            try:
                vpk_package = vpk.open(str(file_path))
                if not vpk_package:
                    logging.error(f"Failed to open VPK file (empty package): {file_path}")
                    return []
            except vpk.VPKError as e:
                logging.error(f"VPK error processing {file_path}: {e}")
                return []
            except Exception as e:
                logging.error(f"Failed to open VPK file {file_path}: {e}")
                return []
                
            texture_paths = []
            sound_paths = []
            
            # Process each file in the VPK
            try:
                for file_path in vpk_package:
                    try:
                        # Check if it's a texture file
                        if file_path.lower().endswith('.vtf') and 'materials/' in file_path.lower():
                            texture_paths.append(file_path)
                        
                        # Check if it's a C4 sound file
                        c4_config = self.config.get("C4_SOUND_REPLACEMENT", {})
                        if c4_config.get("enabled", False) and file_path.lower().endswith('.wav') and 'sound/' in file_path.lower():
                            # Check if the file matches any of the C4 sound patterns
                            file_path_lower = file_path.lower()
                            if any(pattern.lower() in file_path_lower for pattern in c4_config.get("patterns", [])):
                                sound_paths.append(file_path)
                    except Exception as e:
                        logging.debug(f"Error processing file {file_path} in VPK: {e}")
                        continue
            except Exception as e:
                logging.error(f"Error iterating VPK contents {file_path}: {e}")
                return []
            
            # Store sound paths for later processing
            if sound_paths:
                self.c4_sound_paths.extend(sound_paths)
                    
            return texture_paths
            
        except Exception as e:
            logging.error(f"Error processing VPK file {file_path}: {e}")
            return []
    
    def process_bsp_file(self, file_path: Path) -> List[str]:
        """Process a BSP file and extract embedded textures."""
        try:
            if not file_path.exists():
                return []
                
            texture_paths = []
            
            # Read BSP file in chunks
            with open(file_path, 'rb') as f:
                try:
                    # Read BSP header
                    header = f.read(8)  # BSP header is typically 8 bytes
                    if len(header) < 8:  # Invalid/corrupted BSP
                        return []
                        
                    # Check for different BSP versions
                    header_ident = header[:4]
                    if header_ident not in [b'VBSP', b'IBSP', b'RBSP']:
                        return []  # Silently skip files with unknown BSP versions
                        
                    version = struct.unpack('I', header[4:8])[0]
                    
                    # Skip to lump directory
                    f.seek(8)
                    
                    # Read texture lump (lump 2 in Source engine)
                    texture_lump_offset = struct.unpack('I', f.read(4))[0]
                    texture_lump_size = struct.unpack('I', f.read(4))[0]
                    
                    if texture_lump_size > 0 and texture_lump_size < file_path.stat().st_size:
                        try:
                            f.seek(texture_lump_offset)
                            texture_data = f.read(texture_lump_size)
                            
                            # Process texture entries
                            offset = 0
                            while offset < len(texture_data):
                                try:
                                    # Read texture name (null-terminated string)
                                    name_end = texture_data.find(b'\0', offset)
                                    if name_end == -1 or name_end == offset:
                                        break
                                        
                                    name_bytes = texture_data[offset:name_end]
                                    try:
                                        name = name_bytes.decode('ascii', errors='ignore').strip()
                                        if name and name.lower().endswith('.vtf'):
                                            # Add materials/ prefix if not present
                                            if not name.lower().startswith('materials/'):
                                                name = f"materials/{name}"
                                            texture_paths.append(name)
                                    except UnicodeDecodeError:
                                        pass
                                        
                                    # Move to next texture entry (128-byte alignment)
                                    offset = (name_end + 128) & ~127
                                    
                                except Exception:
                                    break
                                    
                        except Exception:
                            pass
                            
                except Exception:
                    pass
                    
            return texture_paths
            
        except Exception:
            return []
    
    def process_gma_file(self, file_path: Path) -> List[str]:
        """Process a GMA (Garry's Mod Addon) file and extract textures."""
        try:
            if not file_path.exists():
                logging.error(f"File not found: {file_path}")
                return []
                
            texture_paths = []
            
            # Read GMA file
            try:
                with open(file_path, 'rb') as f:
                    # Check GMA header
                    header = f.read(4)
                    if header != b'GMAD':
                        return []  # Silently skip invalid GMA files
                        
                    # Skip version and SteamID
                    f.seek(13)
                    
                    # Read file entries
                    while True:
                        try:
                            # Read file path length
                            length_data = f.read(1)
                            if not length_data:  # End of file
                                break
                                
                            path_length = length_data[0]
                            if path_length == 0:  # End of entries
                                break
                                
                            # Read file path
                            try:
                                file_path = f.read(path_length).decode('ascii', errors='ignore')
                                
                                if file_path.lower().endswith('.vtf') and 'materials/' in file_path.lower():
                                    texture_paths.append(file_path)
                            except UnicodeDecodeError:
                                continue  # Skip invalid paths
                                
                            # Skip file size and CRC
                            f.seek(8, 1)
                        except Exception:
                            break  # Break on any error reading entries
                            
                return texture_paths
                
            except Exception:
                return []  # Return empty list on file read errors
                
        except Exception:
            return []  # Return empty list on any other errors
    
    def get_c4_sound_paths(self):
        """Get the list of C4 sound paths found during processing."""
        return self.c4_sound_paths
