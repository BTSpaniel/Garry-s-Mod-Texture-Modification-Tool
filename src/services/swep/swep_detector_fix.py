"""
SWEP Detector Fix Module

This module provides a fix for the SWEP detector to use the new modular implementation
while maintaining backward compatibility.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Union

# Import both detector implementations
from .swep_detector import SWEPDetector as OriginalSWEPDetector
from .swep_detector_new import SWEPDetector as NewSWEPDetector

class SWEPDetector(NewSWEPDetector):
    """
    Enhanced SWEP Detector that uses the new modular implementation
    while maintaining backward compatibility with the original API.
    """
    
    def __init__(self, config: Dict = None, game_path: Optional[str] = None):
        """
        Initialize the SWEPDetector with the new modular implementation.
        
        Args:
            config: Configuration dictionary with detector settings
            game_path: Path to the game directory (e.g., Garry's Mod)
        """
        # Log that we're using the enhanced detector
        logging.info("Using enhanced SWEP detector with modular implementation")
        
        # Initialize with the new implementation
        super().__init__(config, game_path)
        
        # For backward compatibility, keep a reference to the original detector
        # in case we need to fall back to it
        self._original_detector = None
    
    def _get_original_detector(self):
        """
        Get an instance of the original detector for fallback purposes.
        
        Returns:
            Instance of the original SWEPDetector
        """
        if self._original_detector is None:
            self._original_detector = OriginalSWEPDetector(self.config, self.game_path)
        return self._original_detector
    
    def scan_for_sweps(self, game_path=None, progress_callback=None):
        """
        Scan for SWEPs using the new implementation with fallback to original.
        
        Args:
            game_path: Path to Garry's Mod installation. If None, uses previously set path.
            progress_callback: Callback function for progress updates
            
        Returns:
            Dictionary of detected SWEPs
        """
        try:
            # Try using the new implementation
            return super().scan_for_sweps(game_path, progress_callback)
        except Exception as e:
            # Log the error
            logging.error(f"Error using new SWEP detector: {e}")
            logging.info("Falling back to original SWEP detector")
            
            # Fall back to the original implementation
            original = self._get_original_detector()
            if game_path:
                original.set_game_path(game_path)
            return original.scan_for_sweps(game_path, progress_callback)
