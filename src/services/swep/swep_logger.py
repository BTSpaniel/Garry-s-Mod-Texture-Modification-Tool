"""
SWEP Logger Module for SWEP Detector

This module handles logging of SWEP detection results.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Set, Optional


def debug_print(msg):
    """Print debug message with timestamp and thread ID"""
    thread_id = threading.get_ident()
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{timestamp}][Thread-{thread_id}] {msg}")


class SWEPLogger:
    """Handles logging of SWEP detection results."""
    
    def __init__(self, debug_trace: bool = True):
        """
        Initialize the SWEPLogger.
        
        Args:
            debug_trace: Whether to enable debug tracing
        """
        self.logger = logging.getLogger(__name__)
        self.debug_trace = debug_trace
    
    def log_detection_result(self, file_path: Path, detected_sweps: Dict, texture_refs: Set[str], model_refs: Set[str]):
        """
        Log detailed information about detected SWEPs and their assets.
        
        Args:
            file_path: Path to the file
            detected_sweps: Dictionary of detected SWEPs
            texture_refs: Set of texture references
            model_refs: Set of model references
        """
        if not detected_sweps:
            return
        
        if self.debug_trace:
            debug_print(f"Detected {len(detected_sweps)} SWEPs in {file_path}")
            
            for weapon_name, weapon_info in detected_sweps.items():
                debug_print(f"  SWEP: {weapon_name}")
                
                if 'PrintName' in weapon_info:
                    debug_print(f"    Display Name: {weapon_info['PrintName']}")
                
                if 'Base' in weapon_info:
                    debug_print(f"    Base: {weapon_info['Base']}")
                
                if 'ViewModel' in weapon_info:
                    debug_print(f"    ViewModel: {weapon_info['ViewModel']}")
                
                if 'WorldModel' in weapon_info:
                    debug_print(f"    WorldModel: {weapon_info['WorldModel']}")
            
            if texture_refs:
                debug_print(f"  Found {len(texture_refs)} texture references")
                for texture in list(texture_refs)[:5]:  # Show first 5 textures
                    debug_print(f"    Texture: {texture}")
                if len(texture_refs) > 5:
                    debug_print(f"    ... and {len(texture_refs) - 5} more")
            
            if model_refs:
                debug_print(f"  Found {len(model_refs)} model references")
                for model in list(model_refs)[:5]:  # Show first 5 models
                    debug_print(f"    Model: {model}")
                if len(model_refs) > 5:
                    debug_print(f"    ... and {len(model_refs) - 5} more")
    
    def log_scan_stats(self, stats: Dict):
        """
        Log statistics about the SWEP detection process.
        
        Args:
            stats: Dictionary of statistics
        """
        if self.debug_trace:
            debug_print("SWEP Detection Statistics:")
            debug_print(f"  SWEPs detected: {stats.get('sweps_detected', 0)}")
            debug_print(f"  Lua files processed: {stats.get('lua_files_processed', 0)}")
            debug_print(f"  Lua cache files processed: {stats.get('lua_cache_files_processed', 0)}")
            debug_print(f"  Textures found: {stats.get('textures_found', 0)}")
            debug_print(f"  Models found: {stats.get('models_found', 0)}")
            debug_print(f"  Addons scanned: {stats.get('addons_scanned', 0)}")
            debug_print(f"  Workshop items scanned: {stats.get('workshop_items_scanned', 0)}")
    
    def log_export_result(self, output_file: Path, success: bool):
        """
        Log the result of exporting SWEP data.
        
        Args:
            output_file: Path to the output file
            success: Whether the export was successful
        """
        if self.debug_trace:
            if success:
                debug_print(f"Successfully exported SWEP data to {output_file}")
            else:
                debug_print(f"Failed to export SWEP data to {output_file}")
