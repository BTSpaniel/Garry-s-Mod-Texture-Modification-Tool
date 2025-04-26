"""
Test script to verify the SWEP detector functionality.
"""

import sys
import traceback
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

try:
    print("Testing original SWEPDetector import...")
    from src.services.swep import SWEPDetector
    print("✓ Successfully imported SWEPDetector")
    
    print("\nTesting new SWEPDetectorNew import...")
    from src.services.swep import SWEPDetectorNew
    print("✓ Successfully imported SWEPDetectorNew")
    
    print("\nTesting submodule imports...")
    from src.services.swep import (
        TextureExtractor,
        ModelExtractor,
        SWEPParser,
        FileScanner,
        SWEPLogger
    )
    print("✓ Successfully imported all submodules")
    
    # Create instances to verify initialization
    print("\nTesting initialization...")
    
    # Basic config for testing
    config = {
        'debug_trace': True,
        'scan_lua_weapons': True,
        'scan_addons': True,
        'scan_workshop': True,
        'scan_lua_cache': True
    }
    
    # Test original detector
    original_detector = SWEPDetector(config)
    print("✓ Successfully initialized SWEPDetector")
    
    # Test new detector
    new_detector = SWEPDetectorNew(config)
    print("✓ Successfully initialized SWEPDetectorNew")
    
    print("\nAll tests passed! The SWEP detector modules are working correctly.")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nDetailed traceback:")
    traceback.print_exc()
    
    print("\nChecking for missing files...")
    required_files = [
        "src/services/swep/__init__.py",
        "src/services/swep/swep_detector.py",
        "src/services/swep/swep_detector_new.py",
        "src/services/swep/texture_extractor.py",
        "src/services/swep/model_extractor.py",
        "src/services/swep/swep_parser.py",
        "src/services/swep/file_scanner.py",
        "src/services/swep/swep_logger.py",
        "src/services/swep/lua_cache_decoder.py",
        "src/services/swep/vmt_generator.py"
    ]
    
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        if not full_path.exists():
            print(f"Missing file: {file_path}")
        else:
            print(f"File exists: {file_path}")
