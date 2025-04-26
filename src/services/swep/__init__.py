"""
SWEP detection and processing modules for Source Engine Asset Manager
"""

# Import the fixed SWEPDetector that uses the new implementation while maintaining compatibility
from .swep_detector_fix import SWEPDetector
from .lua_cache_decoder import LuaCacheDecoder
from .vmt_generator import VMTGenerator

# Import the new modular components
from .swep_detector_new import SWEPDetector as SWEPDetectorNew
from .texture_extractor import TextureExtractor
from .model_extractor import ModelExtractor
from .swep_parser import SWEPParser
from .file_scanner import FileScanner
from .swep_logger import SWEPLogger

__all__ = [
    # Main modules
    'SWEPDetector', 
    'LuaCacheDecoder', 
    'VMTGenerator',
    
    # New modular components
    'SWEPDetectorNew',
    'TextureExtractor',
    'ModelExtractor',
    'SWEPParser',
    'FileScanner',
    'SWEPLogger'
]
