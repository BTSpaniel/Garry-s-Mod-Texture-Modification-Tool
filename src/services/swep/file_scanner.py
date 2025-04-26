"""
File Scanner Module for SWEP Detector

This module handles scanning of different file types for SWEP definitions.
"""

import os
import re
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .lua_cache_decoder import LuaCacheDecoder
from .swep_parser import SWEPParser


def debug_print(msg):
    """Print debug message with timestamp and thread ID"""
    thread_id = threading.get_ident()
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{timestamp}][Thread-{thread_id}] {msg}")


class FileScanner:
    """Handles scanning of different file types for SWEP definitions."""
    
    def __init__(self, config: Dict = None):
        """
        Initialize the FileScanner.
        
        Args:
            config: Configuration dictionary with scanner settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize the Lua cache decoder
        self.lua_decoder = LuaCacheDecoder(config)
        
        # Initialize the SWEP parser
        self.swep_parser = SWEPParser(config)
        
        # Debug flag
        self.debug_trace = self.config.get('debug_trace', True)
    
    def is_file_processable(self, file_path: Path) -> Tuple[bool, str]:
        """
        Comprehensive check to determine if a file is likely to contain SWEP data.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Tuple of (is_processable, reason)
        """
        # Check if file exists
        if not file_path.exists():
            return False, "File does not exist"
        
        # Check file extension
        valid_extensions = self.config.get('lua_file_extensions', {'.lua', '.luac', '.txt', '.dat'})
        if file_path.suffix.lower() not in valid_extensions and not file_path.name.endswith('.lua.cache'):
            return False, f"Invalid file extension: {file_path.suffix}"
        
        # Check file size (skip empty or very large files)
        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                return False, "File is empty"
            
            # Skip files larger than 10MB (likely not a weapon script)
            if file_size > 10 * 1024 * 1024:
                return False, f"File too large: {file_size} bytes"
        except Exception as e:
            return False, f"Error checking file size: {e}"
        
        # Check file name for weapon-related patterns
        filename_lower = file_path.name.lower()
        
        # Skip common non-weapon files
        skip_patterns = [
            'init.lua',
            'cl_init.lua',
            'shared.lua',
            'autorun',
            'menu',
            'derma',
            'vgui',
            'gamemode',
            'language',
            'translations',
            'config',
            'settings',
            'util',
            'helper',
            'framework',
            'library',
            'lib/',
            'includes',
            'thirdparty',
            'third-party',
            'vendor',
            'external'
        ]
        
        for pattern in skip_patterns:
            if pattern in filename_lower:
                return False, f"Skipped due to pattern: {pattern}"
        
        # Check for weapon-related patterns in the file name
        weapon_patterns = [
            'weapon',
            'swep',
            'gun',
            'pistol',
            'rifle',
            'shotgun',
            'sniper',
            'knife',
            'melee',
            'sword',
            'nade',
            'grenade',
            'explosive',
            'bomb',
            'projectile',
            'launcher',
            'ammo',
            'bullet'
        ]
        
        for pattern in weapon_patterns:
            if pattern in filename_lower:
                return True, f"Matched weapon pattern: {pattern}"
        
        # If we're still not sure, do a quick content check for large files
        if file_size > 100 * 1024:  # For files larger than 100KB
            try:
                # Read first 4KB of the file
                with open(file_path, 'rb') as f:
                    header = f.read(4096)
                
                # Check for binary patterns
                binary_patterns = self.config.get('binary_patterns', [
                    rb'models/weapons',
                    rb'materials/models/weapons',
                    rb'SWEP\.',
                    rb'ViewModel',
                    rb'WorldModel'
                ])
                
                for pattern in binary_patterns:
                    if pattern in header:
                        return True, f"Matched binary pattern: {pattern}"
                
                # If it's a text file, check for text patterns
                try:
                    header_text = header.decode('utf-8', errors='ignore')
                    text_patterns = [
                        'SWEP.',
                        'ViewModel',
                        'WorldModel',
                        'weapons.Register',
                        'scripted_weapon'
                    ]
                    
                    for pattern in text_patterns:
                        if pattern in header_text:
                            return True, f"Matched text pattern: {pattern}"
                except:
                    pass
                
                return False, "No weapon patterns found in file header"
            except Exception as e:
                # If we can't read the file, assume it's not processable
                return False, f"Error reading file header: {e}"
        
        # For smaller files, assume they might be processable
        return True, "Small file, might contain weapon data"
    
    def file_might_contain_weapon_data(self, file_path: Path) -> bool:
        """
        Quick check if a file might contain weapon data based on name and size.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file might contain weapon data, False otherwise
        """
        is_processable, _ = self.is_file_processable(file_path)
        return is_processable
    
    def process_lua_cache_file(self, lc_file: Path, progress_callback: Callable = None) -> Tuple[Set[str], Set[str], Dict, bool]:
        """
        Process a Lua cache file (.lc) using specialized decoding.
        
        Args:
            lc_file: Path to the Lua cache file
            progress_callback: Callback function for progress updates
            
        Returns:
            Tuple of (texture_refs, model_refs, detected_sweps, success)
        """
        try:
            if self.debug_trace:
                debug_print(f"Processing Lua cache file: {lc_file.name}")
            
            # Decode the Lua cache file
            decoded_content = self.lua_decoder.decode_file(lc_file)
            
            if not decoded_content:
                if self.debug_trace:
                    debug_print(f"Failed to decode Lua cache file: {lc_file.name}")
                return set(), set(), {}, False
            
            # Check if this file contains SWEP definitions
            swep_patterns = [
                r'SWEP\.Base\s*=',
                r'SWEP\.PrintName\s*=',
                r'SWEP\.ViewModel\s*=',
                r'SWEP\.WorldModel\s*=',
                r'SWEP\.Primary\s*=',
                r'SWEP\.Secondary\s*=',
                r'weapons\.Register\(',
                r'scripted_weapon\s*=',
                r'WEAPON\.'
            ]
            
            is_swep_file = False
            for pattern in swep_patterns:
                if re.search(pattern, decoded_content, re.IGNORECASE):
                    is_swep_file = True
                    break
            
            if not is_swep_file:
                return set(), set(), {}, False
            
            # Parse the decoded content
            detected_sweps, texture_refs, model_refs = self.swep_parser.parse_lua_file(lc_file)
            
            # Update progress if callback is provided
            if progress_callback:
                progress_callback("cache_processing", 0, 0, f"Processed {lc_file.name}")
            
            return texture_refs, model_refs, detected_sweps, True
            
        except Exception as e:
            if self.debug_trace:
                debug_print(f"Error processing Lua cache file {lc_file.name}: {e}")
            return set(), set(), {}, False
    
    def process_workshop_cache_file(self, lc_file: Path, progress_callback: Callable = None) -> Tuple[Set[str], Set[str], Dict, bool]:
        """
        Process a workshop cache file using specialized methods.
        
        Args:
            lc_file: Path to the workshop cache file
            progress_callback: Callback function for progress updates
            
        Returns:
            Tuple of (texture_refs, model_refs, detected_sweps, success)
        """
        try:
            if self.debug_trace:
                debug_print(f"Processing workshop cache file: {lc_file.name}")
            
            # For workshop files, we need to handle them differently
            # First, check if this is a Lua cache file
            if lc_file.suffix.lower() == '.cache':
                # Decode the Lua cache file
                decoded_content = self.lua_decoder.decode_workshop_file(lc_file)
                
                if not decoded_content:
                    if self.debug_trace:
                        debug_print(f"Failed to decode workshop cache file: {lc_file.name}")
                    return set(), set(), {}, False
                
                # Check if this file contains SWEP definitions
                swep_patterns = [
                    r'SWEP\.Base\s*=',
                    r'SWEP\.PrintName\s*=',
                    r'SWEP\.ViewModel\s*=',
                    r'SWEP\.WorldModel\s*=',
                    r'SWEP\.Primary\s*=',
                    r'SWEP\.Secondary\s*=',
                    r'weapons\.Register\(',
                    r'scripted_weapon\s*=',
                    r'WEAPON\.'
                ]
                
                is_swep_file = False
                for pattern in swep_patterns:
                    if re.search(pattern, decoded_content, re.IGNORECASE):
                        is_swep_file = True
                        break
                
                if not is_swep_file:
                    return set(), set(), {}, False
                
                # Create a temporary file for parsing
                temp_file = Path(f"{lc_file}.temp")
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(decoded_content)
                
                # Parse the decoded content
                detected_sweps, texture_refs, model_refs = self.swep_parser.parse_lua_file(temp_file)
                
                # Remove the temporary file
                try:
                    os.remove(temp_file)
                except:
                    pass
                
                # Update progress if callback is provided
                if progress_callback:
                    progress_callback("workshop_processing", 0, 0, f"Processed {lc_file.name}")
                
                return texture_refs, model_refs, detected_sweps, True
            
            return set(), set(), {}, False
            
        except Exception as e:
            if self.debug_trace:
                debug_print(f"Error processing workshop cache file {lc_file.name}: {e}")
            return set(), set(), {}, False
    
    def process_regular_lua_file(self, lua_file: Path, progress_callback: Callable = None) -> Tuple[Set[str], Set[str], Dict, bool]:
        """
        Process a regular Lua file.
        
        Args:
            lua_file: Path to the Lua file
            progress_callback: Callback function for progress updates
            
        Returns:
            Tuple of (texture_refs, model_refs, detected_sweps, success)
        """
        try:
            if self.debug_trace:
                debug_print(f"Processing regular Lua file: {lua_file.name}")
            
            # Check if this file might contain weapon data
            if not self.file_might_contain_weapon_data(lua_file):
                return set(), set(), {}, False
            
            # Parse the Lua file
            detected_sweps, texture_refs, model_refs = self.swep_parser.parse_lua_file(lua_file)
            
            # Update progress if callback is provided
            if progress_callback:
                progress_callback("lua_processing", 0, 0, f"Processed {lua_file.name}")
            
            return texture_refs, model_refs, detected_sweps, len(detected_sweps) > 0
            
        except Exception as e:
            if self.debug_trace:
                debug_print(f"Error processing regular Lua file {lua_file.name}: {e}")
            return set(), set(), {}, False
    
    def process_cache_file(self, lc_file: Path, progress_callback: Callable = None) -> Tuple[Set[str], Set[str], Dict, bool]:
        """
        Process a single cache file in a worker thread using specialized methods based on file type.
        
        Args:
            lc_file: Path to the cache file
            progress_callback: Callback function for progress updates
            
        Returns:
            Tuple containing (texture_refs, model_refs, detected_sweps, success)
        """
        # Check if this file might contain weapon data
        if not self.file_might_contain_weapon_data(lc_file):
            return set(), set(), {}, False
        
        # Check file type and process accordingly
        if lc_file.name.endswith('.lua.cache'):
            return self.process_lua_cache_file(lc_file, progress_callback)
        elif 'workshop' in str(lc_file).lower() and lc_file.suffix.lower() == '.cache':
            return self.process_workshop_cache_file(lc_file, progress_callback)
        elif lc_file.suffix.lower() in ['.lua', '.luac', '.txt', '.dat']:
            return self.process_regular_lua_file(lc_file, progress_callback)
        else:
            return set(), set(), {}, False
