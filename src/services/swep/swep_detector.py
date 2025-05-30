"""
SWEPDetector Module for Source Engine Asset Manager

This module detects and processes Scripted Weapons (SWEPs). It locates SWEP definitions,
parses their SWEP tables, and extracts all texture references, including ViewModel,
WorldModel, custom materials, and any VMT/VTF links.
"""

import os
import re
import logging
import os
import time
import itertools
import concurrent.futures
import traceback
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        
        # Initialize the Lua cache decoder
        self.lua_decoder = LuaCacheDecoder(config)
        
        # Load configuration
        self._load_config()
        
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
            'lua_file_extensions': {'.lua', '.luac', '.txt', '.dat'},
            'model_extensions': {'.mdl'},
            'texture_extensions': {'.vtf'},
            'weapon_model_patterns': [
                'SWEP.ViewModel',
                'SWEP.WorldModel',
                ':SetModel',
                'self.ViewModel',
                'self.WorldModel',
                '.ViewModel =',
                '.WorldModel =',
                'weapons/',
                'v_',
                'w_',
                'models/weapons',
                'models/v_',
                'models/w_'
            ],
            'weapon_texture_patterns': [
                'weapons/',
                'v_',
                'w_',
                'hands/',
                'arms/',
                'models/weapons',
                'materials/weapons',
                'materials/models/weapons'
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
        
        # Merge with provided config
        for key, default_value in default_config.items():
            if key not in self.config:
                self.config[key] = default_value
    
    def set_game_path(self, game_path: Union[str, Path]):
        """
        Set the game path.
        
        Args:
            game_path: Path to the game directory
        """
        self.game_path = Path(game_path)
    
    def scan_for_sweps(self, game_path: Optional[Union[str, Path]] = None, progress_callback=None) -> Dict:
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
            logging.error("No game path set. Use set_game_path() first.")
            return {}
            
        logging.info(f"Scanning for SWEPs in {self.game_path}")
        
        # Reset collections and stats
        self.detected_sweps = {}
        self.texture_references = set()
        self.model_references = set()
        self.stats = {
            'sweps_detected': 0,
            'lua_files_processed': 0,
            'lua_cache_files_processed': 0,
            'textures_found': 0,
            'models_found': 0,
            'addons_scanned': 0,
            'workshop_items_scanned': 0
        }
        
        # Define scan phases and their weights
        scan_phases = []
        if self.config['scan_lua_weapons']:
            scan_phases.append(('lua_weapons', 0.2))
        if self.config['scan_addons']:
            scan_phases.append(('addons', 0.3))
        if self.config['scan_workshop']:
            scan_phases.append(('workshop', 0.3))
        if self.config['scan_lua_cache']:
            scan_phases.append(('lua_cache', 0.2))
            
        # Track overall progress
        total_phases = len(scan_phases)
        completed_phases = 0
        
        # Helper function to update progress
        def update_progress(phase, current, total, message=""):
            if progress_callback:
                # Calculate phase progress (0-1 within the phase)
                phase_progress = current / max(1, total)
                
                # Calculate overall progress (0-1 across all phases)
                phase_weight = next((w for p, w in scan_phases if p == phase), 0.25)
                overall_progress = (completed_phases + phase_progress) / total_phases
                
                progress_callback(phase, overall_progress, phase_progress, message)
        
        # Scan in configured locations
        for phase, _ in scan_phases:
            if phase == 'lua_weapons':
                update_progress('lua_weapons', 0, 1, "Scanning Lua weapons directory")
                self._scan_lua_weapons(update_progress)
                completed_phases += 1
                
            elif phase == 'addons':
                update_progress('addons', 0, 1, "Scanning addons directory")
                self._scan_addons(update_progress)
                completed_phases += 1
                
            elif phase == 'workshop':
                update_progress('workshop', 0, 1, "Scanning workshop content")
                self._scan_workshop(update_progress)
                completed_phases += 1
                
            elif phase == 'lua_cache':
                update_progress('lua_cache', 0, 1, "Scanning Lua cache files")
                self._scan_lua_cache(update_progress)
                completed_phases += 1
        
        # Final progress update
        if progress_callback:
            progress_callback('complete', 1.0, 1.0, f"Found {len(self.detected_sweps)} SWEPs")
            
        logging.info(f"Found {len(self.detected_sweps)} SWEPs")
        logging.info(f"Found {len(self.texture_references)} texture references")
        
        # Update stats
        self.stats['sweps_detected'] = len(self.detected_sweps)
        self.stats['textures_found'] = len(self.texture_references)
        self.stats['models_found'] = len(self.model_references)
        
        return self.detected_sweps
    
    def get_stats(self) -> Dict:
        """Get detailed statistics about the SWEP detection process."""
        # Update the counts from our collections
        self.stats['sweps_detected'] = len(self.detected_sweps)
        self.stats['textures_found'] = len(self.texture_references)
        self.stats['models_found'] = len(self.model_references)
        
        return self.stats
        
    def get_texture_references(self) -> List[str]:
        """Get all texture references found in SWEPs."""
        return list(self.texture_references)
    
    def get_model_references(self) -> List[str]:
        """Get all model references found in SWEPs."""
        return list(self.model_references)
    
    def _scan_lua_weapons(self, progress_callback=None):
        """Scan the lua/weapons directory for SWEPs."""
        weapons_dir = self.game_path / self.config['folders']['lua_weapons']
        if not weapons_dir.exists():
            logging.warning(f"Lua weapons directory not found: {weapons_dir}")
            return
            
        logging.info(f"Scanning lua/weapons directory: {weapons_dir}")
        
        # Get list of files first for progress tracking
        lua_files = list(weapons_dir.glob("*.lua"))
        total_files = len(lua_files)
        
        for i, lua_file in enumerate(lua_files):
            try:
                self._process_lua_file(lua_file)
                self.stats['lua_files_processed'] += 1
                
                # Update progress
                if progress_callback:
                    progress_callback('lua_weapons', i+1, total_files, f"Processing {lua_file.name}")
                    
            except Exception as e:
                logging.error(f"Error processing {lua_file}: {e}")
    
    def _scan_addons(self, progress_callback=None):
        """Scan the addons directory for SWEPs."""
        addons_dir = self.game_path / self.config['folders']['addons']
        if not addons_dir.exists():
            logging.warning(f"Addons directory not found: {addons_dir}")
            return
            
        logging.info(f"Scanning addons directory: {addons_dir}")
        
        # Get list of addon directories first for progress tracking
        addon_dirs = [d for d in addons_dir.iterdir() if d.is_dir()]
        total_addons = len(addon_dirs)
        
        for i, addon_dir in enumerate(addon_dirs):
            logging.info(f"Scanning addon: {addon_dir.name}")
            self.stats['addons_scanned'] += 1
            
            # Update progress for this addon
            if progress_callback:
                progress_callback('addons', i+1, total_addons, f"Scanning addon: {addon_dir.name}")
            
            # Check for lua/weapons directory in the addon
            weapons_dir = addon_dir / "lua" / "weapons"
            if weapons_dir.exists():
                lua_files = list(weapons_dir.glob("*.lua"))
                
                for j, lua_file in enumerate(lua_files):
                    try:
                        self._process_lua_file(lua_file)
                        self.stats['lua_files_processed'] += 1
                        
                        # Update sub-progress
                        if progress_callback and len(lua_files) > 0:
                            sub_progress = (i + (j+1)/len(lua_files)) / total_addons
                            progress_callback('addons', sub_progress, (j+1)/len(lua_files), 
                                             f"Processing {addon_dir.name}/{lua_file.name}")
                            
                    except Exception as e:
                        logging.error(f"Error processing {lua_file}: {e}")
    
    def _scan_workshop(self, progress_callback=None):
        """Scan the workshop directory for SWEPs."""
        workshop_dir = self.game_path / self.config['folders']['workshop']
        if not workshop_dir.exists():
            logging.warning(f"Workshop directory not found: {workshop_dir}")
            return
            
        logging.info(f"Scanning workshop directory: {workshop_dir}")
        
        # Get list of workshop items first for progress tracking
        item_dirs = [d for d in workshop_dir.iterdir() if d.is_dir()]
        total_items = len(item_dirs)
        
        for i, item_dir in enumerate(item_dirs):
            logging.info(f"Scanning workshop item: {item_dir.name}")
            self.stats['workshop_items_scanned'] += 1
            
            # Update progress for this workshop item
            if progress_callback:
                progress_callback('workshop', i+1, total_items, f"Scanning workshop item: {item_dir.name}")
            
            # Check for lua/weapons directory in the workshop item
            weapons_dir = item_dir / "lua" / "weapons"
            if weapons_dir.exists():
                lua_files = list(weapons_dir.glob("*.lua"))
                
                for j, lua_file in enumerate(lua_files):
                    try:
                        self._process_lua_file(lua_file)
                        self.stats['lua_files_processed'] += 1
                        
                        # Update sub-progress
                        if progress_callback and len(lua_files) > 0:
                            sub_progress = (i + (j+1)/len(lua_files)) / total_items
                            progress_callback('workshop', sub_progress, (j+1)/len(lua_files), 
                                             f"Processing {item_dir.name}/{lua_file.name}")
                            
                    except Exception as e:
                        logging.error(f"Error processing {lua_file}: {e}")
    
    def _scan_lua_cache(self, progress_callback=None):
        """Scan the Lua cache directory for SWEPs using parallel processing."""
        debug_print("ENTER _scan_lua_cache method")
        start_time = time.time()
        
        # First try the standard path
        cache_dir = self.game_path / "garrysmod" / "cache"
        
        # If that doesn't exist, try the config path
        if not cache_dir.exists():
            cache_dir = self.game_path / self.config['folders']['lua_cache']
            if not cache_dir.exists():
                # Try to find the cache directory directly
                potential_paths = [
                    self.game_path / "garrysmod" / "cache",
                    self.game_path / "cache",
                    Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/cache")
                ]
                
                for path in potential_paths:
                    if path.exists():
                        cache_dir = path
                        logging.info(f"Found cache directory at: {cache_dir}")
                        break
                else:
                    logging.warning("Could not find Lua cache directory")
                    return
        
        logging.info(f"Scanning Lua cache directory: {cache_dir}")
        
        # Look for ALL files in the cache directory, not just specific extensions
        # This ensures we don't miss any cached Lua files
        lc_files = []
        
        # Scan all files in the cache directory
        try:
            for file_path in cache_dir.glob("**/*"):
                if file_path.is_file():
                    lc_files.append(file_path)
        except Exception as e:
            logging.error(f"Error scanning cache directory: {e}")
        
        # Check multiple potential Lua file locations
        potential_dirs = [
            # Cache directories
            self.game_path / "garrysmod" / "cache" / "workshop",
            self.game_path / "garrysmod" / "cache" / "lua",
            Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/cache/workshop"),
            Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/cache/lua"),
            
            # Lua directories
            self.game_path / "garrysmod" / "lua",
            self.game_path / "garrysmod" / "addons",
            Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/lua"),
            Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/addons"),
            
            # Workshop content
            self.game_path / "garrysmod" / "addons" / "workshop",
            Path("J:/SteamLibrary/steamapps/workshop/content/4000"),  # Workshop content for GMod
            
            # Additional Steam library paths
            Path("C:/Program Files (x86)/Steam/steamapps/common/GarrysMod/garrysmod/lua"),
            Path("C:/Program Files (x86)/Steam/steamapps/common/GarrysMod/garrysmod/addons"),
            Path("D:/Steam/steamapps/common/GarrysMod/garrysmod/lua"),
            Path("D:/Steam/steamapps/common/GarrysMod/garrysmod/addons"),
            Path("E:/Steam/steamapps/common/GarrysMod/garrysmod/lua"),
            Path("E:/Steam/steamapps/common/GarrysMod/garrysmod/addons"),
        ]
        
        # Scan all potential directories
        for dir_path in potential_dirs:
            if dir_path.exists():
                logging.info(f"Scanning directory: {dir_path}")
                try:
                    # Use a more targeted glob pattern to find Lua files
                    for pattern in ["**/*.lua", "**/*.lc", "**/*.luac", "**/*.txt", "**/*.dat"]:
                        for file_path in dir_path.glob(pattern):
                            if file_path.is_file():
                                lc_files.append(file_path)
                    
                    # Also scan for files without extensions that might be Lua files
                    for file_path in dir_path.glob("**/*"):
                        if file_path.is_file() and not file_path.suffix:
                            lc_files.append(file_path)
                except Exception as e:
                    logging.error(f"Error scanning directory {dir_path}: {e}")
        
        # First attempt to decode all files to find Lua content, then filter
        debug_print(f"Starting file decoding and filtering, total files to check: {len(lc_files)}")
        filtered_files = []
        skipped_count = 0
        skip_reasons = {
            "file_not_exist": 0,
            "empty_file": 0,
            "file_too_large": 0,
            "decode_failed": 0,
            "no_lua_content": 0,
            "error": 0
        }
        accepted_reasons = {
            "contains_lua": 0,
            "contains_swep": 0,
            "contains_weapon": 0,
            "contains_model": 0,
            "contains_texture": 0
        }
        
        # Process files in batches to show progress
        batch_size = 1000
        for i in range(0, len(lc_files), batch_size):
            batch = lc_files[i:i+batch_size]
            debug_print(f"Processing batch {i//batch_size + 1}/{(len(lc_files) + batch_size - 1)//batch_size}, files {i+1}-{min(i+batch_size, len(lc_files))}")
            
            for file_path in batch:
                try:
                    # Skip files that don't exist or are empty
                    if not file_path.exists():
                        skipped_count += 1
                        skip_reasons["file_not_exist"] += 1
                        continue
                        
                    file_size = file_path.stat().st_size
                    if file_size == 0:
                        skipped_count += 1
                        skip_reasons["empty_file"] += 1
                        continue
                        
                    # Skip extremely large files
                    if file_size > 20 * 1024 * 1024:  # 20MB
                        skipped_count += 1
                        skip_reasons["file_too_large"] += 1
                        continue
                    
                    # Try to decode the file first with timeout protection
                    decoded_content = None
                    try:
                        # Start a timer to prevent hanging on a single file
                        start_time = time.time()
                        
                        # First try a quick check with binary read
                        with open(file_path, 'rb') as f:
                            content = f.read(4096)  # Read first 4KB
                            # Convert binary to string for pattern matching
                            quick_content = content.decode('utf-8', errors='ignore')
                        
                        # If the quick check shows promising content, try full decoding
                        if ('SWEP' in quick_content or 'weapon' in quick_content.lower() or 
                            'function' in quick_content or 'models/' in quick_content or
                            'materials/' in quick_content):
                            
                            # Only attempt full decoding if quick check passes
                            try:
                                # Use the LuaCacheDecoder to attempt decoding with timeout
                                decoded_content = self.lua_decoder.decode_file(file_path)
                                
                                # Check if decoding took too long
                                if time.time() - start_time > 2.0:  # 2 second timeout
                                    debug_print(f"Decoding took too long for {file_path}, using quick content")
                                    decoded_content = quick_content
                            except Exception as decode_e:
                                debug_print(f"Decoding failed for {file_path}, using quick content: {decode_e}")
                                decoded_content = quick_content
                        else:
                            # Use the quick content if no promising patterns found
                            decoded_content = quick_content
                            
                    except Exception as e:
                        debug_print(f"Error reading file {file_path}: {e}")
                    
                    # If we couldn't get any content, skip
                    if not decoded_content:
                        skipped_count += 1
                        skip_reasons["decode_failed"] += 1
                        continue
                    
                    # Check for Lua, SWEP, weapon, model, or texture patterns in the decoded content
                    # Use a more efficient approach to check multiple patterns at once
                    reason = None
                    content_lower = decoded_content.lower()
                    
                    # Check for the most important patterns first
                    if "swep" in content_lower:
                        reason = "contains_swep"
                    elif "weapon" in content_lower:
                        reason = "contains_weapon"
                    elif "function" in content_lower and ("local" in content_lower or "return" in content_lower):
                        reason = "contains_lua"
                    elif "models/" in content_lower:
                        reason = "contains_model"
                    elif "materials/" in content_lower:
                        reason = "contains_texture"
                    
                    if reason:
                        filtered_files.append(file_path)
                        if reason in accepted_reasons:
                            accepted_reasons[reason] += 1
                        else:
                            accepted_reasons[reason] = 1
                    else:
                        skipped_count += 1
                        skip_reasons["no_lua_content"] += 1
                except Exception as e:
                    skipped_count += 1
                    skip_reasons["error"] += 1
                    debug_print(f"Error processing file {file_path}: {e}")
            
            # Show progress after each batch
            if (i + batch_size) % (batch_size * 5) == 0 or (i + batch_size) >= len(lc_files):
                debug_print(f"Processed {i + min(batch_size, len(lc_files) - i)}/{len(lc_files)} files, kept {len(filtered_files)} so far")
        
        debug_print(f"File filtering complete. Kept {len(filtered_files)}, skipped {skipped_count} total")
        debug_print(f"Skipped breakdown: {skip_reasons}")
        debug_print(f"Accepted breakdown: {accepted_reasons}")
        
        total_files = len(filtered_files)
        logging.info(f"Found {total_files} cache files to process after filtering")
        
        # Create a thread pool with workers based on CPU count
        max_workers = min(16, os.cpu_count() or 4)  # Reduced max workers to prevent overload
        logging.info(f"Processing cache files with {max_workers} parallel workers")
        print(f"Processing {total_files} cache files with {max_workers} parallel workers")
        
        # Log the number of files found by extension
        extension_counts = {}
        for file_path in filtered_files:
            ext = file_path.suffix.lower()
            if ext in extension_counts:
                extension_counts[ext] += 1
            else:
                extension_counts[ext] = 1
        
        logging.info(f"Files by extension: {extension_counts}")
        
        # Process files in chunks to avoid memory issues
        chunk_size = 500
        processed_count = 0
        
        # Track results from parallel processing
        texture_refs = set()
        model_refs = set()
        detected_sweps = {}
        processed_files_count = 0
        
        # Process in chunks
        for chunk_start in range(0, total_files, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_files)
            chunk = filtered_files[chunk_start:chunk_end]
            
            if progress_callback:
                progress_callback('lua_cache', processed_count, total_files, 
                                 f"Processing files {chunk_start+1}-{chunk_end} of {total_files}")
            
            # Process this chunk in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks with a timeout to prevent hanging
                debug_print(f"Submitting tasks for chunk {chunk_start+1}-{chunk_end}")
                future_to_file = {}
                for lc_file in chunk:
                    # We've already filtered files, so no need to check size again
                    # Just verify the file still exists
                    try:
                        if not lc_file.exists():
                            debug_print(f"File no longer exists: {lc_file}")
                            continue
                    except Exception as e:
                        debug_print(f"Error checking file: {lc_file}: {str(e)}")
                        continue
                        
                    debug_print(f"Submitting task for file: {lc_file}")
                    future = executor.submit(self._process_cache_file, lc_file, progress_callback)
                    future_to_file[future] = lc_file
                
                debug_print(f"Submitted {len(future_to_file)} tasks for processing")
                
                # Process results as they complete with timeout
                try:
                    debug_print("Waiting for tasks to complete...")
                    completed_count = 0
                    
                    for i, future in enumerate(concurrent.futures.as_completed(future_to_file, timeout=30)):
                        completed_count += 1
                        lc_file = future_to_file[future]
                        processed_count += 1
                        
                        debug_print(f"Task completed for file: {lc_file} ({completed_count}/{len(future_to_file)})")
                        
                        # Update progress every 10 files
                        if processed_count % 10 == 0:
                            status_msg = f"Processed {processed_count}/{total_files} files"
                            print(status_msg)
                            if progress_callback:
                                progress_callback('lua_cache', processed_count, total_files, status_msg)
                        
                        try:
                            # Get results from the worker with a timeout
                            debug_print(f"Getting results for {lc_file}")
                            result = future.result(timeout=3)  # Reduced timeout
                            
                            if result:
                                file_textures, file_models, file_sweps, success = result
                                
                                # Update our collections with the results
                                texture_refs.update(file_textures)
                                model_refs.update(file_models)
                                detected_sweps.update(file_sweps)
                                
                                # Update stats immediately
                                self.stats['textures_found'] += len(file_textures)
                                self.stats['models_found'] += len(file_models)
                                if file_sweps:
                                    self.stats['sweps_detected'] += len(file_sweps)
                                
                                if success:
                                    processed_files_count += 1
                                    debug_print(f"Successfully processed {lc_file}")
                        except concurrent.futures.TimeoutError:
                            error_msg = f"WARNING: Processing timed out for {lc_file.name}"
                            print(error_msg)
                            logging.warning(error_msg)
                            debug_print(f"TIMEOUT getting results for {lc_file}")
                        except Exception as e:
                            error_msg = f"ERROR: Failed to process {lc_file.name}: {str(e)}"
                            print(error_msg)
                            logging.error(error_msg)
                            debug_print(f"EXCEPTION getting results for {lc_file}: {str(e)}")
                            traceback.print_exc()
                except concurrent.futures.TimeoutError:
                    error_msg = f"CRITICAL: Overall processing timed out after 30 seconds. Cancelling remaining tasks."
                    print(error_msg)
                    logging.critical(error_msg)
                        
                    # Cancel any remaining futures to avoid hanging
                cancelled_count = 0
                for future in future_to_file:
                    if not future.done():
                        future.cancel()
                        cancelled_count += 1
                
                if cancelled_count > 0:
                    print(f"Cancelled {cancelled_count} unfinished tasks to prevent hanging")
                    logging.warning(f"Cancelled {cancelled_count} unfinished tasks to prevent hanging")
        
        # Update the main collections with results from parallel processing
        self.texture_references.update(texture_refs)
        self.model_references.update(model_refs)
        self.detected_sweps.update(detected_sweps)
        self.stats['lua_cache_files_processed'] += processed_files_count
        
        elapsed_time = time.time() - start_time
        status_msg = f"Processed {processed_files_count} cache files in {elapsed_time:.2f} seconds"
        print(status_msg)
        logging.info(status_msg)
        
    def _process_cache_file(self, lc_file: Path, progress_callback=None) -> Tuple[Set[str], Set[str], Dict, bool]:
        """Process a single cache file in a worker thread using specialized methods based on file type.
        
        Returns:
            Tuple containing (texture_refs, model_refs, detected_sweps, success)
        """
        texture_refs = set()
        model_refs = set()
        detected_sweps = {}
        success = False
        
        try:
            debug_print(f"START processing file: {lc_file}")
            
            # We've already filtered by size, so no need to check again
            # Just determine file type based on extension and path
            file_ext = lc_file.suffix.lower()
            file_name = lc_file.name.lower()
            file_path_str = str(lc_file).lower()
            
            debug_print(f"File type analysis: ext={file_ext}, name={file_name}")
            
            # Process based on file type
            if 'workshop' in file_path_str:
                # Workshop cache file
                debug_print(f"Routing to workshop processor: {lc_file}")
                return self._process_workshop_cache_file(lc_file, progress_callback)
            elif file_ext == '.lc' or '/lua/cache/' in file_path_str:
                # Lua cache file
                debug_print(f"Routing to Lua cache processor: {lc_file}")
                return self._process_lua_cache_file(lc_file, progress_callback)
            else:
                # Regular Lua file
                debug_print(f"Routing to regular Lua processor: {lc_file}")
                return self._process_regular_lua_file(lc_file, progress_callback)
                
        except Exception as e:
            error_msg = f"Error processing cache file {lc_file.name}: {str(e)}"
            logging.error(error_msg)
            debug_print(error_msg)
            traceback.print_exc()
            return set(), set(), {}, False

    def _is_file_processable(self, file_path: Path) -> Tuple[bool, str]:
        """Comprehensive check to determine if a file is likely to contain SWEP data.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Tuple of (is_processable, reason)
        """
        try:
            # Skip files that don't exist
            if not file_path.exists():
                return False, "file_not_exist"
                
            # Skip empty files
            file_size = file_path.stat().st_size
            if file_size == 0:
                return False, "empty_file"
                
            # Skip files larger than 10MB
            if file_size > 10 * 1024 * 1024:
                return False, "file_too_large"
            
            # Get file name and extension
            file_name = file_path.name.lower()
            file_ext = file_path.suffix.lower()
            file_path_str = str(file_path).lower()
            
            # Define extensions to skip completely
            skip_extensions = {
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tga', '.vtf', '.mdl', '.wav', '.mp3',
                '.vmt', '.pcf', '.ttf', '.otf', '.dll', '.exe', '.zip', '.rar', '.7z', '.tar', '.gz',
                '.bz2', '.ico', '.cur', '.ani', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.dat', '.bin', '.pak', '.vpk', '.bsp', '.nav', '.ain', '.vbsp', '.vvis', '.vrad',
                '.svg', '.tif', '.tiff', '.webp', '.mp4', '.webm', '.avi', '.mov', '.wmv', '.flv',
                '.ogg', '.aac', '.wma', '.flac', '.mid', '.midi', '.json', '.xml', '.csv', '.txt',
                '.cfg', '.ini', '.log', '.db', '.sql', '.sqlite', '.mdb', '.accdb', '.db3', '.s3db'
            }
            
            # Skip files with extensions that definitely aren't Lua cache
            # Only skip if we're certain it's not a Lua file with a weird extension
            if file_ext in skip_extensions and not ('weapon' in file_name.lower() or 'swep' in file_name.lower()):
                return False, "extension_skipped"
            
            # Always include files with these extensions
            if file_ext.lower() in ['.lua', '.lc', '.luac', '', '.txt', '.dat', '.json', '.vmt', '.vtf', '.mdl']:
                return True, "lua_extension"
                
            # Always include files in these directories
            key_directories = [
                # Core Lua logic
                'lua/weapons', 'lua/sweps', 'lua/entities', 'lua/effects',
                'lua/autorun', 'lua/includes', 'lua/vgui', 'lua/derma',
                'lua/menu', 'lua/wire', 'lua/hooks', 'lua/skins',
                'lua/items', 'lua/jobs', 'lua/config', 'lua/npcs',
                'lua/postprocess', 'lua/skins', 'lua/modules',
                'lua/terrortown', 'lua/ttt', 'lua/darkrp', 'lua/ulx', 'lua/ulib',
                'lua/express', 'lua/pac3', 'lua/pac', 'lua/falco',
                
                # Content roots
                'addons/', 'addons/weapons', 'addons/entities', 'addons/lua',
                'addons/materials', 'addons/models', 'addons/sound', 'addons/particles',
                
                # Asset directories
                'materials/', 'models/', 'sound/', 'scripts/', 'particles/',
                'data/', 'resource/', 'resource/fonts/', 'backgrounds/',

                # Game structure
                'gamemodes/', 'garrysmod/lua', 'garrysmod/gamemodes', 'garrysmod/addons',
                'garrysmod/data', 'garrysmod/materials', 'garrysmod/models',
                
                # Misc/rare folders
                'maps/', 'maps/soundcache/', 'download/', 'downloads/', 'media/',
                'workshop/', 'workshop/materials', 'workshop/models', 'workshop/lua',
                'cache/', 'lua/cache', 'cfg/', 'html/', 'shaders/'
            ]
            for directory in key_directories:
                if directory.lower() in file_path_str.lower():
                    return True, "key_directory"
            
            # Define prefixes that indicate likely SWEP content, GMod, and popular gamemodes
            useful_prefixes = [
                # SWEP and weapon prefixes
                'swep', 'weapon', 'gun', 'rifle', 'pistol', 'shotgun', 'sniper', 'knife', 'nade',
                'grenade', 'explosive', 'bomb', 'sword', 'melee', 'projectile', 'ammo', 'bullet',
                'shell', 'magazine', 'clip', 'scope', 'sight', 'barrel', 'trigger', 'hammer', 'stock',
                'grip', 'handle', 'silencer', 'suppressor', 'muzzle', 'flash', 'laser', 'tactical',
                'holster', 'reload', 'shoot', 'fire', 'aim', 'sight', 'crosshair', 'recoil', 'spread',
                'accuracy', 'damage', 'range', 'penetration', 'armor', 'kevlar', 'helmet', 'shield',
                
                # GMod and gamemode-specific prefixes
                'weapon_', 'swep_', 'gun_', 'w_', 'v_',  # Common weapon prefixes
                'gm_', 'sandbox_', 'darkrp_', 'ttt_', 'murder_',  # Popular gamemodes
                'prop_', 'puzzle_', 'srp_', 'sb_', 'zombies_',  # Other game-related prefixes
                'rp_', 'flood_', 'build_', 'escape_', 'hide_',  # More gamemodes and content
                'stranded_', 'deathrun_', 'ph_', 'climbing_',  # Additional gamemodes
                'csgo_', 'tf2_', 'bunnyhop_', 'surf_',  # Common GMod game content
                'barrage_', 'block_', 'fallout_', 'cs_',  # Other potential prefixes
                'sky_', 'racing_', 'weapons_', 'ultimate_',  # Racing, weapons, and other content
                'ctf_', 'gmod_', 'rpz_', 'sr_', 'team_',  # Team-based and roleplay gamemodes
                'tardis_', 'lag_', 'noob_', 'jail_',  # Specific or niche gamemodes
                'arena_', 'traps_', 'dl_', 'quest_', 'maze_',  # Additional variety of content
                'gng_', 'juggernaut_', 'capture_', 'scav_',  # More popular and niche
                'rocket_', 'stray_', 'holdout_', 'skirmish_',  # More custom and gamemode prefixes
                
                # Additional common GMod weapon prefixes
                'm9k_', 'fas2_', 'cw_', 'arc_', 'fas_', 'tfa_', 'khr_', 'rw_', 'mg_',
                'eft_', 'arccw_', 'bobs_', 'mw_', 'rust_', 'bf_', 'bf4_', 'bf3_', 'cod_',
                'mw2_', 'mw3_', 'bo_', 'bo2_', 'bo3_', 'waw_', 'doi_', 'ins_', 'ins2_',
                'kf_', 'kf2_', 'l4d_', 'l4d2_', 'cs_', 'css_', 'csgo_', 'gfl_', 'hl_', 'hl2_',
                'dod_', 'dods_', 'tf_', 'tf2_', 'ut_', 'ut2_', 'ut3_', 'ut4_', 'quake_',
                'doom_', 'halo_', 'scp_', 'stalker_', 'metro_', 'fallout_', 'fo_', 'fo3_', 'fo4_',
                'fnv_', 'crysis_', 'fc_', 'fc2_', 'fc3_', 'fc4_', 'fc5_', 'gta_', 'gta4_', 'gta5_',
                'rdr_', 'rdr2_', 'payday_', 'pd_', 'pd2_', 'bf1_', 'bfv_', 'bfh_', 'bfbc_', 'bfbc2_',
                'sw_', 'starwars_', 'swbf_', 'swbf2_', 'jedi_', 'sith_', 'lightsaber_',
                'ac_', 'acr_', 'aco_', 'ac3_', 'ac4_', 'acu_', 'acs_', 'acb_', 'ace_', 'acw_',
                'mgsv_', 'mgs_', 'mgs3_', 'mgs4_', 'mgs5_', 'mw19_', 'mw22_', 'mwii_',
                
                # Specific weapon types and models
                'ak', 'ar', 'm4', 'm16', 'mp5', 'mp7', 'mp9', 'uzi', 'mac10', 'mac11',
                'glock', 'beretta', 'deagle', 'revolver', 'magnum', 'python', 'colt',
                'scar', 'famas', 'galil', 'aug', 'sg', 'g3', 'g36', 'hk', 'fn', 'p90',
                'ump', 'ppsh', 'thompson', 'vector', 'awp', 'scout', 'dragunov', 'svd',
                'mosin', 'kar98', 'springfield', 'enfield', 'garand', 'bar', 'bren',
                'mg42', 'mg34', 'm60', 'm249', 'minigun', 'gatling', 'rpg', 'bazooka',
                'launcher', 'c4', 'claymore', 'mine', 'tnt', 'dynamite', 'semtex',
                'frag', 'smoke', 'flash', 'stun', 'molotov', 'incendiary', 'flame',
                'katana', 'machete', 'axe', 'crowbar', 'hammer', 'bat', 'club', 'pipe',
                'spear', 'bow', 'crossbow', 'arrow', 'bolt', 'dart', 'throwing',
                'rpk', 'pkm', 'pkp', 'mk', 'l85', 'l86', 'l96', 'l115', 'l118', 'l129',
                'vss', 'val', 'vintorez', 'bizon', 'saiga', 'spas', 'benelli', 'mossberg',
                'remington', 'winchester', 'ithaca', 'nova', 'toz', 'aa12', 'usas', 'striker',
                'barret', 'intervention', 'msr', 'dsr', 'cheytac', 'lapua', 'srs', 'tac21',
                'ssg', 'steyr', 'aug', 'tavor', 'tar', 'fal', 'g3', 'g36', 'hk416', 'hk417',
                'm14', 'm1a', 'socom', 'mk11', 'mk12', 'mk14', 'mk17', 'mk18', 'mk20',
                'sr25', 'scar', 'acr', 'honey', 'badger', 'bushmaster', 'sig', 'sauer',
                'p226', 'p228', 'p229', 'p320', 'p365', 'p938', 'm17', 'm18', 'm9',
                '1911', '92fs', 'px4', 'apx', 'cx4', 'cx4storm', 'arx', 'arx160', 'arx200',
                'fnx', 'fnp', 'fiveseven', 'fnscar', 'fnfal', 'fnp90', 'fnps90', 'fnminimi',
                'fnmag', 'fnm249', 'fnm240', 'fnm2010', 'fnballista', 'fnspr', 'fnf2000',
                'fnfs2000', 'fncal', 'fn57', 'fn509', 'fn503', 'fn502', 'fn15', 'fn40gl',
                'fnmk48', 'cz', 'cz75', 'cz85', 'cz97', 'cz52', 'cz82', 'cz83', 'cz100',
                'cz110', 'cz999', 'cz2075', 'cz805', 'cz807', 'cz858', 'vz58', 'vz61',
                'skorpion', 'vz82', 'vz83', 'vz52', 'vz24', 'vz98', 'bren', 'zb26', 'zb30',
                'zb53', 'uk59', 'uk68', 'uk59l', 'vz59', 'vz37', 'vz15', 'vz26', 'vz30',
                'vz33', 'vz35', 'vz38', 'vz42', 'vz43', 'vz44', 'vz45', 'vz47', 'vz52',
                'vz54', 'vz57', 'vz59', 'vz61', 'vz62', 'vz63', 'vz64', 'vz66', 'vz68',
                'vz70', 'vz72', 'vz74', 'vz76', 'vz78', 'vz82', 'vz83', 'vz85', 'vz88',
                'vz90', 'vz91', 'vz92', 'vz95', 'vz97', 'vz98', 'vz99', 'vz01', 'vz04',
                'vz05', 'vz06', 'vz08', 'vz09', 'vz10', 'vz11', 'vz12', 'vz13', 'vz14',
                'vz15', 'vz16', 'vz17', 'vz18', 'vz19', 'vz20', 'vz21', 'vz22', 'vz23',
                'vz24', 'vz25', 'vz26', 'vz27', 'vz28', 'vz29', 'vz30', 'vz31', 'vz32',
                'vz33', 'vz34', 'vz35', 'vz36', 'vz37', 'vz38', 'vz39', 'vz40', 'vz41',
                'vz42', 'vz43', 'vz44', 'vz45', 'vz46', 'vz47', 'vz48', 'vz49', 'vz50'
            ]
            
            # Check if the file name contains any useful prefixes
            # Convert to lowercase for case-insensitive matching
            file_name_lower = file_name.lower()
            for prefix in useful_prefixes:
                if prefix.lower() in file_name_lower:
                    return True, "useful_prefix"
            
            # Quick binary check for files (< 500KB to catch more potential files)
            if file_size < 500 * 1024:
                try:
                    # Read the first 4KB of the file to check if it's binary
                    with open(file_path, 'rb') as f:
                        header = f.read(4096)
                        
                    # Check if it contains any of our binary patterns
                    for pattern in self.config['binary_patterns']:
                        if pattern in header:
                            return True, "binary_pattern"
                except Exception:
                    pass
            
            # If we get here, the file is not useful
            return False, "no_indicators"
            
        except Exception as e:
            debug_print(f"Error checking file {file_path}: {str(e)}")
            return False, f"error: {str(e)}"

    def _file_might_contain_weapon_data(self, file_path: Path):
        """Quick check if a file might contain weapon data based on name and size."""
        # Use the more comprehensive check
        is_processable, _ = self._is_file_processable(file_path)
        return is_processable
    
    def _detect_gamemode(self, base: str, category: str, content: str) -> str:
        """Detect which gamemode a weapon belongs to based on its properties and content."""
        content_lower = content.lower()
        
        # Check for TTT
        ttt_indicators = ['ttt', 'terrortown', 'traitor', 'innocent', 'detective', 'weapon_ttt', 'WEAPON_EQUIP']
        for indicator in ttt_indicators:
            if indicator in content_lower:
                return 'TTT'
        if base and ('weapon_tttbase' in base or 'weapon_tttbasegrenade' in base):
            return 'TTT'
        
        # Check for DarkRP
        darkrp_indicators = ['darkrp', 'rp_', 'arrest', 'unarrest', 'wanted', 'police', 'mayor', 'gangster']
        for indicator in darkrp_indicators:
            if indicator in content_lower:
                return 'DarkRP'
        if category and 'darkrp' in category.lower():
            return 'DarkRP'
        
        # Check for Zombie Survival
        zs_indicators = ['zombiesurvival', 'zombify', 'undead', 'weapon_zs', 'zs_', 'zombie']
        for indicator in zs_indicators:
            if indicator in content_lower:
                return 'Zombie Survival'
        if base and 'weapon_zs_base' in base:
            return 'Zombie Survival'
        
        # Check for Murder
        murder_indicators = ['murder', 'mu_knife', 'mu_magnum', 'murderer', 'bystander']
        for indicator in murder_indicators:
            if indicator in content_lower:
                return 'Murder'
        
        # Check for Prop Hunt
        ph_indicators = ['prop_hunt', 'ph_', 'prophunt', 'ph_prop', 'ph_gun']
        for indicator in ph_indicators:
            if indicator in content_lower:
                return 'Prop Hunt'
        
        # Check for other common gamemodes
        if 'deathrun' in content_lower:
            return 'Deathrun'
        if 'jailbreak' in content_lower or 'jb_' in content_lower:
            return 'Jailbreak'
        if 'bhop' in content_lower:
            return 'Bunny Hop'
        if 'surf' in content_lower:
            return 'Surf'
        if 'cinema' in content_lower:
            return 'Cinema'
        if 'flood' in content_lower:
            return 'Flood'
        
        # Default to Sandbox if no specific gamemode detected
        if base and ('weapon_base' in base or 'gmod_base' in base):
            return 'Sandbox'
            
        return 'Sandbox'
    
    def _process_lua_cache_file(self, lc_file: Path, progress_callback=None) -> Tuple[Set[str], Set[str], Dict, bool]:
        """Process a Lua cache file (.lc) using specialized decoding."""
        texture_refs = set()
        model_refs = set()
        detected_sweps = {}
        success = False
        
        debug_print(f"ENTER _process_lua_cache_file: {lc_file}")
        
        try:
            # Check file size before processing to avoid freezing on large files
            try:
                debug_print(f"Checking file size: {lc_file}")
                file_size = lc_file.stat().st_size
                debug_print(f"File size: {file_size / 1024:.1f} KB")
                
                if file_size > 20 * 1024 * 1024:  # Skip files larger than 20MB (increased from 5MB)
                    skip_msg = f"Skipping large Lua cache file: {lc_file.name} ({file_size / 1024 / 1024:.2f} MB)"
                    print(skip_msg)
                    logging.debug(skip_msg)
                    return texture_refs, model_refs, detected_sweps, False
            except Exception as e:
                error_msg = f"Error checking file size for {lc_file.name}: {str(e)}"
                print(error_msg)
                logging.error(error_msg)
                traceback.print_exc()
                return texture_refs, model_refs, detected_sweps, False
                
            # Use the dedicated Lua cache decoder with a timeout
            debug_print(f"Starting Lua cache decoding: {lc_file}")
            start_time = time.time()
            
            try:
                debug_print(f"Calling lua_decoder.decode_lc_file for {lc_file}")
                decoded_content = self.lua_decoder.decode_lc_file(lc_file)
                debug_print(f"Decoding complete for {lc_file}")
            except Exception as e:
                error_msg = f"Error decoding {lc_file.name}: {str(e)}"
                print(error_msg)
                logging.error(error_msg)
                traceback.print_exc()
                return texture_refs, model_refs, detected_sweps, False
            
            # Check if decoding took too long
            decode_time = time.time() - start_time
            debug_print(f"Decode time: {decode_time:.2f}s for {lc_file}")
            
            if decode_time > 2:  # Reduced timeout from 3 to 2 seconds
                timeout_msg = f"Lua cache decoding took too long for {lc_file.name} ({decode_time:.2f}s)"
                print(timeout_msg)
                logging.debug(timeout_msg)
                
                # Add a small delay to let other threads progress
                time.sleep(0.1)
                
                return texture_refs, model_refs, detected_sweps, False
            
            if decoded_content:
                # Extract texture and model references
                texture_refs.update(self._extract_texture_references_worker(decoded_content))
                model_refs.update(self._extract_model_references_worker(decoded_content))
                
                # Look for various SWEP definition patterns
                # 1. Standard SWEP = {} assignments
                swep_matches = list(re.finditer(r'SWEP\s*=\s*\{([^}]+)\}', decoded_content, re.DOTALL))
                
                # 2. weapons.Register(...) calls
                weapons_register_matches = list(re.finditer(r'weapons\.Register\s*\(\s*([^,]+),\s*["\']([^"\']*)["\'](.*?)\)', decoded_content, re.DOTALL))
                
                # Process standard SWEP definitions
                for match in swep_matches:
                    try:
                        swep_table = match.group(1)
                        swep_info = self._parse_swep_table(swep_table)
                        
                        if not swep_info:
                            continue
                            
                        swep_name = swep_info.get('PrintName', 'Unknown')
                        swep_class = lc_file.stem
                        swep_base = swep_info.get('Base', 'weapon_base')
                        swep_category = swep_info.get('Category', '')
                        
                        # Determine gamemode
                        gamemode = self._detect_gamemode(swep_base, swep_category, decoded_content)
                        
                        # Store enhanced SWEP info
                        detected_sweps[swep_class] = {
                            'name': swep_name,
                            'class': swep_class,
                            'base': swep_base,
                            'category': swep_category,
                            'gamemode': gamemode,
                            'file': str(lc_file),
                        }
                    except Exception as e:
                        debug_print(f"Error parsing SWEP table: {e}")
                
                # Process weapons.Register calls
                for match in weapons_register_matches:
                    try:
                        table_var = match.group(1).strip()
                        weapon_class = match.group(2).strip()
                        
                        # Try to find the table definition
                        table_def_pattern = f"{table_var}\s*=\s*\{{([^}}]+)\}}"
                        table_matches = list(re.finditer(table_def_pattern, decoded_content, re.DOTALL))
                        
                        if table_matches:
                            table_content = table_matches[0].group(1)
                            weapon_info = self._parse_swep_table(table_content)
                            
                            if not weapon_info:
                                continue
                                
                            weapon_name = weapon_info.get('PrintName', 'Unknown')
                            weapon_base = weapon_info.get('Base', 'weapon_base')
                            weapon_category = weapon_info.get('Category', '')
                            
                            # Determine gamemode
                            gamemode = self._detect_gamemode(weapon_base, weapon_category, decoded_content)
                            
                            # Store enhanced weapon info
                            detected_sweps[weapon_class] = {
                                'name': weapon_name,
                                'class': weapon_class,
                                'base': weapon_base,
                                'category': weapon_category,
                                'gamemode': gamemode,
                                'file': str(lc_file),
                                'registration': 'weapons.Register'
                            }
                    except Exception as e:
                        debug_print(f"Error parsing weapons.Register: {e}")
                
                success = True
        except Exception as e:
            logging.debug(f"Lua cache decoding failed for {lc_file.name}: {e}")
            
        return texture_refs, model_refs, detected_sweps, success
    
    def _process_workshop_cache_file(self, lc_file: Path, progress_callback=None) -> Tuple[Set[str], Set[str], Dict, bool]:
        """Process a workshop cache file using specialized methods."""
        texture_refs = set()
        model_refs = set()
        detected_sweps = {}
        success = False
        
        debug_print(f"ENTER _process_workshop_cache_file: {lc_file}")
        start_time = time.time()
        
        # Update progress if callback provided
        if progress_callback:
            progress_callback('workshop_cache', 0, 1, f"Processing workshop file: {lc_file.name}")
        
        try:
            # Quick check for file size to avoid processing large files
            try:
                file_size = lc_file.stat().st_size
                debug_print(f"Workshop file size: {file_size / 1024:.1f} KB")
                
                if file_size > 10 * 1024 * 1024:  # Skip files larger than 10MB
                    skip_msg = f"Skipping large workshop file: {lc_file.name} ({file_size / 1024 / 1024:.2f} MB)"
                    print(skip_msg)
                    logging.debug(skip_msg)
                    if progress_callback:
                        progress_callback('workshop_cache', 1, 1, skip_msg)
                    return texture_refs, model_refs, detected_sweps, False
            except Exception as e:
                debug_print(f"Error checking workshop file size: {str(e)}")
                if progress_callback:
                    progress_callback('workshop_cache', 1, 1, f"Error: {str(e)}")
                return texture_refs, model_refs, detected_sweps, False
                
            # Read the file content as binary with timeout protection
            # Start a timer to prevent hanging on a single file
            read_start = time.time()
            
            # Update progress
            if progress_callback:
                progress_callback('workshop_cache', 0.2, 1, f"Reading file: {lc_file.name}")
            
            try:
                with open(lc_file, 'rb') as f:
                    # Only read up to 10MB to avoid memory issues
                    binary_content = f.read(10 * 1024 * 1024)
                    
                read_time = time.time() - read_start
                if read_time > 1.0:  # Log slow file reads
                    debug_print(f"WARNING: Slow file read: {read_time:.2f}s for {lc_file}")
                    
                # If reading took too long, add a small delay to let other threads progress
                if read_time > 2.0:
                    time.sleep(0.1)  # Small delay to prevent UI freezing
                    
                debug_print(f"Read {len(binary_content)} bytes from workshop file")
            except Exception as e:
                debug_print(f"Error reading workshop file: {str(e)}")
                if progress_callback:
                    progress_callback('workshop_cache', 1, 1, f"Error reading file: {str(e)}")
                return texture_refs, model_refs, detected_sweps, False
                
            # Extract weapon model and texture paths directly
            # This is much faster than full decoding for workshop files
            debug_print("Converting binary to text for pattern matching")
            text_content = binary_content.decode('utf-8', errors='ignore')
            
            # Look for specific workshop patterns with timeout protection
            debug_print("Searching for weapon model patterns")
            pattern_start = time.time()
            
            # Update progress
            if progress_callback:
                progress_callback('workshop_cache', 0.4, 1, f"Analyzing model patterns: {lc_file.name}")
            
            # Limit text content to first 500KB to avoid regex hanging
            limited_text = text_content[:500000]
            
            try:
                for i, pattern in enumerate(self.config['weapon_model_patterns']):
                    # Update progress for each pattern
                    if progress_callback and len(self.config['weapon_model_patterns']) > 0:
                        pattern_progress = 0.4 + (i / len(self.config['weapon_model_patterns'])) * 0.2
                        progress_callback('workshop_cache', pattern_progress, 1, 
                                         f"Pattern {i+1}/{len(self.config['weapon_model_patterns'])}: {lc_file.name}")
                    
                    # Set a time limit for each pattern
                    if time.time() - pattern_start > 2.0:  # If we've spent more than 2 seconds on patterns
                        debug_print(f"WARNING: Pattern matching taking too long, skipping remaining patterns")
                        break
                        
                    try:
                        safe_pattern = f"['\"]([^'\"]*{re.escape(pattern)}[^'\"]*\.mdl)['\"]|([^\s]*{re.escape(pattern)}[^\s]*\.mdl)"
                        model_matches = list(re.finditer(safe_pattern, limited_text, re.IGNORECASE))
                        
                        # Limit to first 50 matches
                        match_count = 0
                        for match in model_matches[:50]:
                            model_path = match.group(1) or match.group(2)
                            if model_path:
                                model_refs.add(model_path.replace('\\', '/'))
                                success = True
                                match_count += 1
                                
                        if match_count > 0:
                            debug_print(f"Found {match_count} matches for model pattern '{pattern}'")
                    except Exception as e:
                        debug_print(f"Error in model pattern '{pattern}': {str(e)}")
                        continue
            except Exception as e:
                debug_print(f"Error in model pattern processing: {str(e)}")
            
            # Reset pattern timer for texture patterns
            pattern_start = time.time()
            debug_print("Searching for weapon texture patterns")
            
            # Update progress
            if progress_callback:
                progress_callback('workshop_cache', 0.6, 1, f"Analyzing texture patterns: {lc_file.name}")
            
            try:
                for i, pattern in enumerate(self.config['weapon_texture_patterns']):
                    # Update progress for each pattern
                    if progress_callback and len(self.config['weapon_texture_patterns']) > 0:
                        pattern_progress = 0.6 + (i / len(self.config['weapon_texture_patterns'])) * 0.2
                        progress_callback('workshop_cache', pattern_progress, 1, 
                                         f"Texture pattern {i+1}/{len(self.config['weapon_texture_patterns'])}: {lc_file.name}")
                    
                    # Set a time limit for each pattern
                    if time.time() - pattern_start > 2.0:  # If we've spent more than 2 seconds on patterns
                        debug_print(f"WARNING: Texture pattern matching taking too long, skipping remaining patterns")
                        break
                        
                    try:
                        safe_pattern = f"['\"]([^'\"]*{re.escape(pattern)}[^'\"]*\.vtf)['\"]|([^\s]*{re.escape(pattern)}[^\s]*\.vtf)"
                        texture_matches = list(re.finditer(safe_pattern, limited_text, re.IGNORECASE))
                        
                        # Limit to first 50 matches
                        match_count = 0
                        for match in texture_matches[:50]:
                            texture_path = match.group(1) or match.group(2)
                            if texture_path:
                                texture_refs.add(texture_path.replace('\\', '/'))
                                success = True
                                match_count += 1
                                
                        if match_count > 0:
                            debug_print(f"Found {match_count} matches for texture pattern '{pattern}'")
                    except Exception as e:
                        debug_print(f"Error in texture pattern '{pattern}': {str(e)}")
                        continue
            except Exception as e:
                debug_print(f"Error in texture pattern processing: {str(e)}")
            
            # Additional general texture search
            debug_print("Searching for additional texture references")
            pattern_start = time.time()
            
            try:
                # Use a simple findall with limited text
                texture_matches = re.findall(r'materials\/[\w\/\-\.]+\.(vmt|vtf)', limited_text, re.IGNORECASE)
                
                if time.time() - pattern_start > 1.0:  # Log slow pattern matching
                    debug_print(f"WARNING: Slow texture pattern matching: {time.time() - pattern_start:.2f}s")
                    
                match_count = 0
                for texture in texture_matches[:100]:  # Limit to first 100 matches
                    texture_refs.add(texture)
                    match_count += 1
                    
                debug_print(f"Found {match_count} additional texture references")
            except Exception as e:
                debug_print(f"Error in additional texture pattern matching: {str(e)}")
                
            # Look for SWEP table references
            debug_print("Searching for SWEP references")
            pattern_start = time.time()
            
            try:
                # Use a simple findall with limited text
                swep_matches = re.findall(r'SWEP\.([\w_]+)\s*=\s*["\']([^"\']*)["\'\s]', limited_text)
                
                if time.time() - pattern_start > 1.0:  # Log slow pattern matching
                    debug_print(f"WARNING: Slow SWEP pattern matching: {time.time() - pattern_start:.2f}s")
                    
                if swep_matches:
                    swep_name = lc_file.stem
                    detected_sweps[swep_name] = {
                        'name': swep_name,
                        'properties': {prop: value for prop, value in swep_matches[:50]}  # Limit properties
                    }
                    debug_print(f"Found SWEP: {swep_name} with {len(swep_matches)} properties")
            except Exception as e:
                debug_print(f"Error in SWEP pattern matching: {str(e)}")
                
            success = True
            debug_print(f"Workshop file processing completed in {time.time() - start_time:.2f}s")
            
            # Final progress update
            if progress_callback:
                progress_callback('workshop_cache', 1, 1, f"Completed: {lc_file.name}")
                
            # Update stats
            self.stats['workshop_items_scanned'] += 1
            self.stats['textures_found'] += len(texture_refs)
            self.stats['models_found'] += len(model_refs)
            if detected_sweps:
                self.stats['sweps_detected'] += len(detected_sweps)
                
            return texture_refs, model_refs, detected_sweps, success
            
        except Exception as e:
            error_msg = f"Error processing workshop cache file {lc_file.name}: {e}"
            print(error_msg)
            logging.error(error_msg)
            debug_print(f"EXCEPTION in workshop file processing: {str(e)}")
            traceback.print_exc()
            
            # Error progress update
            if progress_callback:
                progress_callback('workshop_cache', 1, 1, f"Error: {lc_file.name}")
                
            return texture_refs, model_refs, detected_sweps, False
        
    def _process_regular_lua_file(self, lua_file: Path, progress_callback=None) -> Tuple[Set[str], Set[str], Dict, bool]:
        """Process a regular Lua file."""
        texture_refs = set()
        model_refs = set()
        detected_sweps = {}
        success = False
        
        try:
            with open(lua_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Only process if it contains weapon-related content
            if self._is_likely_swep(content):
                # Extract texture and model references
                texture_refs.update(self._extract_texture_references_worker(content))
                model_refs.update(self._extract_model_references_worker(content))
                
                # Look for various SWEP definition patterns
                # 1. Standard SWEP = {} assignments
                swep_matches = list(re.finditer(r'SWEP\s*=\s*\{([^}]+)\}', decoded_content, re.DOTALL))
                
                # 2. weapons.Register(...) calls
                weapons_register_matches = list(re.finditer(r'weapons\.Register\s*\(\s*([^,]+),\s*["\']([^"\']*)["\'](.*?)\)', decoded_content, re.DOTALL))
                
                # Process standard SWEP definitions
                for match in swep_matches:
                    try:
                        swep_table = match.group(1)
                        swep_info = self._parse_swep_table(swep_table)
                        
                        if not swep_info:
                            continue
                            
                        swep_name = swep_info.get('PrintName', 'Unknown')
                        swep_class = lc_file.stem
                        swep_base = swep_info.get('Base', 'weapon_base')
                        swep_category = swep_info.get('Category', '')
                        
                        # Determine gamemode
                        gamemode = self._detect_gamemode(swep_base, swep_category, decoded_content)
                        
                        # Store enhanced SWEP info
                        detected_sweps[swep_class] = {
                            'name': swep_name,
                            'class': swep_class,
                            'base': swep_base,
                            'category': swep_category,
                            'gamemode': gamemode,
                            'file': str(lc_file),
                        }
                    except Exception as e:
                        debug_print(f"Error parsing SWEP table: {e}")
                
                # Process weapons.Register calls
                for match in weapons_register_matches:
                    try:
                        table_var = match.group(1).strip()
                        weapon_class = match.group(2).strip()
                        
                        # Try to find the table definition
                        table_def_pattern = f"{table_var}\s*=\s*\{{([^}}]+)\}}"
                        table_matches = list(re.finditer(table_def_pattern, decoded_content, re.DOTALL))
                        
                        if table_matches:
                            table_content = table_matches[0].group(1)
                            weapon_info = self._parse_swep_table(table_content)
                            
                            if not weapon_info:
                                continue
                                
                            weapon_name = weapon_info.get('PrintName', 'Unknown')
                            weapon_base = weapon_info.get('Base', 'weapon_base')
                            weapon_category = weapon_info.get('Category', '')
                            
                            # Determine gamemode
                            gamemode = self._detect_gamemode(weapon_base, weapon_category, decoded_content)
                            
                            # Store enhanced weapon info
                            detected_sweps[weapon_class] = {
                                'name': weapon_name,
                                'class': weapon_class,
                                'base': weapon_base,
                                'category': weapon_category,
                                'gamemode': gamemode,
                                'file': str(lc_file),
                                'registration': 'weapons.Register'
                            }
                    except Exception as e:
                        debug_print(f"Error parsing weapons.Register: {e}")
                
                success = True
        except Exception as e:
            logging.debug(f"Regular Lua processing failed for {lua_file.name}: {e}")
            return set(), set(), {}, False

    def _extract_texture_references_worker(self, content: str) -> Set[str]:
        """Extract texture references from content."""
        texture_refs = set()
        
        # Extract texture paths from Material() calls
        material_matches = re.finditer(r'Material\(\s*["\']([^"\']*)["\'](\s*,\s*[^)]*)?\)', content, re.DOTALL)
        for mat_match in material_matches:
            texture_path = mat_match.group(1)
            if texture_path:
                texture_refs.add(texture_path)
                self.stats['textures_found'] += 1
        
        # Extract VMT/VTF references
        vmt_matches = re.finditer(r'["\'](materials/[^"\']*.(?:vmt|vtf))["\'](\s*,\s*[^)]*)?', content, re.DOTALL)
        for vmt_match in vmt_matches:
            texture_path = vmt_match.group(1)
            if texture_path:
                texture_refs.add(texture_path)
                self.stats['textures_found'] += 1
        
        return texture_refs

    def _parse_swep_table(self, table_content: str) -> Dict[str, str]:
        """Extract key information from a SWEP table definition."""
        swep_info = {}
        
        # Extract key properties using regex
        # Look for PrintName = "...", Base = "...", etc.
        property_pattern = r'([A-Za-z0-9_]+)\s*=\s*["\'](.+?)["\']'
        for match in re.finditer(property_pattern, table_content, re.DOTALL):
            key = match.group(1).strip()
            value = match.group(2).strip()
            
            if key and value:
                swep_info[key] = value
                
                # Track model references
                if key.lower() in ['model', 'worldmodel', 'viewmodel']:
                    if value and isinstance(value, str):
                        self.model_references.add(value)
                        self.stats['models_found'] += 1
        
        # Also look for numeric properties like Slot = 1
        numeric_pattern = r'([A-Za-z0-9_]+)\s*=\s*([0-9]+)'
        for match in re.finditer(numeric_pattern, table_content, re.DOTALL):
            key = match.group(1).strip()
            value = match.group(2).strip()
            
            if key and value:
                swep_info[key] = value
        
        return swep_info
    
    def get_texture_references(self) -> List[str]:
        """
        Get all texture references found during scanning.
        
        Returns:
            List of texture references
        """
        return list(self.texture_references)
    
    def get_model_references(self) -> List[str]:
        """
        Get all model references found during scanning.
        
        Returns:
            List of model references
        """
        return list(self.model_references)
    
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
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting SWEP data: {e}")
            return False
