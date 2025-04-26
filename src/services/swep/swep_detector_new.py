"""
SWEPDetector Module for Source Engine Asset Manager

This module detects and processes Scripted Weapons (SWEPs). It locates SWEP definitions,
parses their SWEP tables, and extracts all texture references, including ViewModel,
WorldModel, custom materials, and any VMT/VTF links.
"""

import os
import json
import logging
import time
import threading
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import submodules
from .texture_extractor import TextureExtractor
from .model_extractor import ModelExtractor
from .swep_parser import SWEPParser
from .file_scanner import FileScanner
from .swep_logger import SWEPLogger
from .lua_cache_decoder import LuaCacheDecoder
from .vmt_generator import VMTGenerator

# Debug flag to enable detailed tracing
DEBUG_TRACE = True


def debug_print(msg):
    """Print debug message with timestamp and thread ID"""
    if DEBUG_TRACE:
        thread_id = threading.get_ident()
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"[{timestamp}][Thread-{thread_id}] {msg}")


class SWEPDetector:
    """
    Handles detection and processing of Scripted Weapons (SWEPs) and their associated textures.
    """
    
    def __init__(self, config: Dict = None, game_path: Optional[str] = None):
        """
        Initialize the SWEPDetector.
        
        Args:
            config: Configuration dictionary with detector settings
            game_path: Path to the game directory (e.g., Garry's Mod)
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.game_path = Path(game_path) if game_path else None
        
        # Load configuration
        self._load_config()
        
        # Initialize submodules
        self.texture_extractor = TextureExtractor(self.config)
        self.model_extractor = ModelExtractor(self.config)
        self.swep_parser = SWEPParser(self.config)
        self.file_scanner = FileScanner(self.config)
        self.swep_logger = SWEPLogger(self.config.get('debug_trace', DEBUG_TRACE))
        self.lua_decoder = LuaCacheDecoder(self.config)
        
        # Results storage
        self.detected_sweps = {}
        self.texture_references = set()
        self.model_references = set()
        
        # Stats tracking
        self.stats = {
            'sweps_detected': 0,
            'lua_files_processed': 0,
            'lua_cache_files_processed': 0,
            'textures_found': 0,
            'models_found': 0,
            'addons_scanned': 0,
            'workshop_items_scanned': 0
        }
    
    def _load_config(self):
        """Load configuration settings or use defaults."""
        default_config = {
            'enabled': True,
            'scan_lua_weapons': True,
            'scan_addons': True,
            'scan_workshop': True,
            'scan_lua_cache': True,
            'force_regenerate': False,
            'debug_trace': DEBUG_TRACE,
            'lua_file_extensions': {'.lua', '.luac', '.txt', '.dat'},
            'model_extensions': {'.mdl'},
            'texture_extensions': {'.vtf'},
            'weapon_model_patterns': [
                'SWEP.ViewModel',
                'SWEP.WorldModel',
                'self.ViewModel',
                'self.WorldModel',
                '.ViewModel =',
                '.WorldModel =',
                ':SetModel',
                'SetModel(',
                'weapons/',
                'v_',
                'w_',
                'models/weapons',
                'models/v_',
                'models/w_',
                'models/c_'
            ],
            'weapon_texture_patterns': [
                'weapons/',
                'v_',
                'w_',
                'c_',
                'hands/',
                'arms/',
                'models/weapons',
                'materials/weapons',
                'materials/models/weapons',
                'materials/vgui',
                'SetMaterial(',
                'SetSubMaterial(',
                'Material('
            ],
            'folders': {
                'lua_cache': 'garrysmod/cache/lua',
                'lua_weapons': 'garrysmod/lua/weapons',
                'addons': 'garrysmod/addons',
                'workshop': 'workshop/content/4000',
                'downloads': 'garrysmod/downloads'
            },
            'binary_patterns': [
                rb'models/weapons',
                rb'materials/models/weapons',
                rb'SWEP\.',
                rb'ViewModel',
                rb'WorldModel'
            ]
        }
        
        # Update config with provided values
        if self.config:
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
        else:
            self.config = default_config
    
    def set_game_path(self, game_path: Union[str, Path]):
        """
        Set the game path.
        
        Args:
            game_path: Path to the game directory
        """
        self.game_path = Path(game_path)
    
    def scan_for_sweps(self, game_path: Optional[Union[str, Path]] = None, progress_callback=None):
        """
        Scan for SWEPs in the game path.
        
        Args:
            game_path: Path to Garry's Mod installation. If None, uses previously set path.
            progress_callback: Callback function for progress updates (phase, current, total, message)
            
        Returns:
            Dictionary of detected SWEPs
        """
        if game_path:
            self.set_game_path(game_path)
        
        if not self.game_path:
            raise ValueError("Game path not set")
        
        # Reset results
        self.detected_sweps = {}
        self.texture_references = set()
        self.model_references = set()
        
        # Reset stats
        self.stats = {
            'sweps_detected': 0,
            'lua_files_processed': 0,
            'lua_cache_files_processed': 0,
            'textures_found': 0,
            'models_found': 0,
            'addons_scanned': 0,
            'workshop_items_scanned': 0
        }
        
        # Define progress update function
        def update_progress(phase, current, total, message=""):
            if progress_callback:
                progress_callback(phase, current, total, message)
            else:
                if total > 0:
                    debug_print(f"{phase}: {current}/{total} - {message}")
                else:
                    debug_print(f"{phase}: {message}")
        
        # Scan lua/weapons directory
        if self.config.get('scan_lua_weapons', True):
            self._scan_lua_weapons(update_progress)
        
        # Scan addons directory
        if self.config.get('scan_addons', True):
            self._scan_addons(update_progress)
        
        # Scan workshop directory
        if self.config.get('scan_workshop', True):
            self._scan_workshop(update_progress)
        
        # Scan lua cache directory
        if self.config.get('scan_lua_cache', True):
            self._scan_lua_cache(update_progress)
        
        # Log stats
        self.swep_logger.log_scan_stats(self.stats)
        
        return self.detected_sweps
    
    def get_stats(self):
        """Get detailed statistics about the SWEP detection process."""
        return self.stats
    
    def get_texture_references(self):
        """Get all texture references found in SWEPs."""
        return list(self.texture_references)
    
    def get_model_references(self):
        """Get all model references found in SWEPs."""
        return list(self.model_references)
    
    def _scan_lua_weapons(self, progress_callback=None):
        """Scan the lua/weapons directory for SWEPs."""
        lua_weapons_path = self.game_path / self.config['folders']['lua_weapons']
        
        if not lua_weapons_path.exists():
            debug_print(f"Lua weapons directory not found: {lua_weapons_path}")
            return
        
        debug_print(f"Scanning lua/weapons directory: {lua_weapons_path}")
        
        # Get all Lua files in the directory
        lua_files = []
        for ext in self.config['lua_file_extensions']:
            lua_files.extend(lua_weapons_path.glob(f"**/*{ext}"))
        
        total_files = len(lua_files)
        debug_print(f"Found {total_files} Lua files in lua/weapons directory")
        
        for i, lua_file in enumerate(lua_files):
            progress_callback("lua_weapons", i + 1, total_files, f"Processing {lua_file.name}")
            
            # Process the Lua file
            texture_refs, model_refs, detected_sweps, success = self.file_scanner.process_regular_lua_file(lua_file, progress_callback)
            
            if success:
                # Update results
                self.texture_references.update(texture_refs)
                self.model_references.update(model_refs)
                self.detected_sweps.update(detected_sweps)
                
                # Log detection result
                self.swep_logger.log_detection_result(lua_file, detected_sweps, texture_refs, model_refs)
    
    def _scan_addons(self, progress_callback=None):
        """Scan the addons directory for SWEPs."""
        addons_path = self.game_path / self.config['folders']['addons']
        
        if not addons_path.exists():
            debug_print(f"Addons directory not found: {addons_path}")
            return
        
        debug_print(f"Scanning addons directory: {addons_path}")
        
        # Get all addon directories
        addon_dirs = [d for d in addons_path.iterdir() if d.is_dir()]
        
        total_addons = len(addon_dirs)
        debug_print(f"Found {total_addons} addons")
        
        for i, addon_dir in enumerate(addon_dirs):
            progress_callback("addons", i + 1, total_addons, f"Processing addon: {addon_dir.name}")
            
            # Look for lua/weapons directory in the addon
            weapons_dir = addon_dir / "lua" / "weapons"
            if weapons_dir.exists():
                # Get all Lua files in the directory
                lua_files = []
                for ext in self.config['lua_file_extensions']:
                    lua_files.extend(weapons_dir.glob(f"**/*{ext}"))
                
                for lua_file in lua_files:
                    # Process the Lua file
                    texture_refs, model_refs, detected_sweps, success = self.file_scanner.process_regular_lua_file(lua_file, progress_callback)
                    
                    if success:
                        # Update results
                        self.texture_references.update(texture_refs)
                        self.model_references.update(model_refs)
                        self.detected_sweps.update(detected_sweps)
                        
                        # Log detection result
                        self.swep_logger.log_detection_result(lua_file, detected_sweps, texture_refs, model_refs)
            
            self.stats['addons_scanned'] += 1
    
    def _scan_workshop(self, progress_callback=None):
        """Scan the workshop directory for SWEPs."""
        workshop_path = self.game_path / self.config['folders']['workshop']
        
        if not workshop_path.exists():
            debug_print(f"Workshop directory not found: {workshop_path}")
            return
        
        debug_print(f"Scanning workshop directory: {workshop_path}")
        
        # Get all workshop item directories
        workshop_items = [d for d in workshop_path.iterdir() if d.is_dir()]
        
        total_items = len(workshop_items)
        debug_print(f"Found {total_items} workshop items")
        
        for i, item_dir in enumerate(workshop_items):
            progress_callback("workshop", i + 1, total_items, f"Processing workshop item: {item_dir.name}")
            
            # Look for lua/weapons directory in the workshop item
            weapons_dir = item_dir / "lua" / "weapons"
            if weapons_dir.exists():
                # Get all Lua files in the directory
                lua_files = []
                for ext in self.config['lua_file_extensions']:
                    lua_files.extend(weapons_dir.glob(f"**/*{ext}"))
                
                for lua_file in lua_files:
                    # Process the Lua file
                    texture_refs, model_refs, detected_sweps, success = self.file_scanner.process_regular_lua_file(lua_file, progress_callback)
                    
                    if success:
                        # Update results
                        self.texture_references.update(texture_refs)
                        self.model_references.update(model_refs)
                        self.detected_sweps.update(detected_sweps)
                        
                        # Log detection result
                        self.swep_logger.log_detection_result(lua_file, detected_sweps, texture_refs, model_refs)
            
            self.stats['workshop_items_scanned'] += 1
    
    def _scan_lua_cache(self, progress_callback=None):
        """Scan the Lua cache directory for SWEPs using parallel processing."""
        lua_cache_path = self.game_path / self.config['folders']['lua_cache']
        
        if not lua_cache_path.exists():
            debug_print(f"Lua cache directory not found: {lua_cache_path}")
            return
        
        debug_print(f"Scanning Lua cache directory: {lua_cache_path}")
        
        # Get all Lua cache files
        cache_files = list(lua_cache_path.glob("**/*.lua.cache"))
        
        total_files = len(cache_files)
        debug_print(f"Found {total_files} Lua cache files")
        
        # Process cache files in parallel
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.file_scanner.process_cache_file, lc_file, progress_callback): lc_file
                for lc_file in cache_files
            }
            
            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_file)):
                lc_file = future_to_file[future]
                progress_callback("lua_cache", i + 1, total_files, f"Processing {lc_file.name}")
                
                try:
                    texture_refs, model_refs, detected_sweps, success = future.result()
                    
                    if success:
                        # Update results
                        self.texture_references.update(texture_refs)
                        self.model_references.update(model_refs)
                        self.detected_sweps.update(detected_sweps)
                        
                        # Log detection result
                        self.swep_logger.log_detection_result(lc_file, detected_sweps, texture_refs, model_refs)
                        
                        self.stats['lua_cache_files_processed'] += 1
                        self.stats['sweps_detected'] += len(detected_sweps)
                        self.stats['textures_found'] += len(texture_refs)
                        self.stats['models_found'] += len(model_refs)
                
                except Exception as e:
                    debug_print(f"Error processing {lc_file.name}: {e}")
    
    def generate_vmt_files(self, output_dir: Union[str, Path], texture_paths: List[str], config: Dict = None) -> int:
        """
        Generate VMT files for the detected textures using the VMTGenerator.
        
        Args:
            output_dir: Directory to write VMT files to
            texture_paths: List of texture paths to generate VMTs for
            config: Configuration dictionary to pass to VMTGenerator
            
        Returns:
            Number of VMT files generated
        """
        # Use the VMTGenerator
        vmt_generator = VMTGenerator(config or self.config)
        
        output_dir = Path(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        count = 0
        for texture_path in texture_paths:
            # Skip if not a texture path
            if not texture_path.endswith('.vtf') and not texture_path.endswith('.vmt'):
                # Try to append .vtf
                texture_path = texture_path.rstrip('/\\') + '.vtf'
            
            # Create output path
            rel_path = texture_path.replace('materials/', '')
            if rel_path.endswith('.vtf'):
                rel_path = rel_path[:-4] + '.vmt'
            elif not rel_path.endswith('.vmt'):
                rel_path = rel_path + '.vmt'
                
            output_path = output_dir / rel_path
            
            # Skip if file already exists
            if output_path.exists() and not self.config.get('force_regenerate', False):
                continue
            
            # Generate VMT content using VMTGenerator
            vmt_content, _ = vmt_generator.create_vmt_content(texture_path)
            
            # Create the VMT file using VMTGenerator's file creation method
            if vmt_generator.create_vmt_file(str(output_path), vmt_content):
                count += 1
            
        return count
    
    def export_swep_data(self, output_file: Union[str, Path]) -> bool:
        """
        Export detected SWEP data to a JSON file.
        
        Args:
            output_file: Path to write JSON file to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_file = Path(output_file)
            os.makedirs(output_file.parent, exist_ok=True)
            
            # Prepare data for export
            export_data = {
                'sweps': self.detected_sweps,
                'texture_references': list(self.texture_references),
                'model_references': list(self.model_references)
            }
            
            # Write JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            # Log export result
            self.swep_logger.log_export_result(output_file, True)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting SWEP data: {e}")
            
            # Log export result
            self.swep_logger.log_export_result(output_file, False)
            
            return False
