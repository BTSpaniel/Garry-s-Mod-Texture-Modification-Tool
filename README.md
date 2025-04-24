# Texture Extractor v1.2.3

A tool to extract and modify Garry's Mod textures.

## Features

- Extracts textures from Source Engine games (GMod, CS:S, HL2, etc.)
- Detects SWEPs (Scripted Weapons) and their associated models/textures
- Scans Lua files for model and texture references
- Decodes Lua cache files (.lc) and Garry's Mod cache files using LZMA decompression
- Generates VMT files for extracted textures
- Supports custom output paths
- Modern GUI with progress tracking
- Includes standalone tools for Lua cache decompression

## Requirements

- Windows operating system
- Python 3.8 or higher
- Source Engine game installation (e.g., Garry's Mod)

## Installation

1. Download the latest release
2. Extract the files to a directory of your choice
3. Run `main.py` to start the application

## Usage

1. Launch the application
2. Select your Garry's Mod directory (or other Source Engine game)
3. Choose an output directory for extracted textures
4. Click "Start Processing"
5. Wait for the process to complete
6. Check the output directory for extracted textures

### Standalone Lua Cache Decompressor

A standalone tool is included to decompress Garry's Mod Lua cache files:

```bash
python tools/gmod_lua_cache_decompressor.py "C:\Path\To\GarrysMod\garrysmod\cache\lua"
```

This will create a `decompressed` folder with all the decompressed Lua files.

## Changelog

### v1.2.3 (2025-04-24)

- Added LZMA decompression support for Garry's Mod Lua cache files
- Added standalone Lua cache decompression tool in the tools folder
- Added detailed step-by-step debugging with timestamps and thread IDs
- Added timeouts and limits for regex pattern matching to prevent freezing
- Improved error handling with detailed stack traces

### v1.2.2 (2025-04-24)

- **Robust Lua Cache Detection**:
  - Completely overhauled Lua cache file detection system
  - Added automatic detection of cache directories across multiple Steam library locations (including J: drive)
  - Implemented multi-format processing for all cache files (binary, Lua cache, plain text)
  - Added comprehensive scanning of all files in cache directories (12,500+ files processed)
  - Added specific scanning of workshop and lua subdirectories in the cache
  - Implemented fallback paths for different Steam library configurations
  - Fixed issues with Lua cache decoder reference
  - Added dedicated methods for texture and model reference extraction
  - Enhanced error handling and logging for cache file processing
  - Added binary pattern matching for encoded cache files

### v1.2.1 (2025-04-24)

- **UI Improvements**:
  - Modernized the GUI with a more beautiful and user-friendly interface
  - Added custom application icon throughout the interface
  - Improved button styling with consistent colors
  - Fixed window sizing and layout issues (950x950 non-resizable)
  - Added proper padding around all elements
  - Made window non-resizable to maintain layout integrity
  - Rebuilt statistics panel with proper alignment

### v1.2.1 (2025-04-22)

- **Improved settings dialog**:
  - Reorganized deletion settings to group checkboxes together
  - Set trees and props deletion to be off by default
  - Added setting for specifying C4 sound replacement file
  - Added helpful sound file suggestions
  - Fixed BooleanVar handling for more reliable settings

### v1.2.0 (2024-03-21)

- **Added VMT deletion system**:
  - Added configurable deletion categories (trees, effects, UI, hands/weapons, props)
  - Added master enable/disable switch for deletion
  - Added per-category enable/disable toggles
  - Added customizable deletion patterns
  - Added deletion statistics tracking
- **Improved GUI**:
  - Enhanced completion message formatting
  - Added thousands separators for large numbers
  - Improved status message readability
  - Added centered text alignment
  - Added consistent font styling

### v1.1.3 (2024-03-21)

- **Added settings system**:
  - Added comprehensive settings dialog
  - Added texture processing settings
  - Added backup configuration
  - Added transparency controls
  - Added performance tuning
  - Added logging configuration
  - Added real-time settings validation
  - Added settings persistence
- **GUI improvements**:
  - Added settings button
  - Improved button layout
  - Enhanced user feedback
  - Added input validation

### v1.1.2 (2024-03-21)

- **Enhanced error handling**:
  - Improved permission handling for file operations
  - Added robust directory creation with multiple fallback methods
  - Enhanced backup verification system
  - Added detailed logging for troubleshooting
  - Improved GUI error reporting
- **Improved file processing**:
  - Added sanitization for file paths
  - Enhanced VPK file handling
  - Added support for more file formats
  - Optimized texture processing
- **GUI improvements**:
  - Added real-time progress updates
  - Enhanced status reporting
  - Improved error visualization
  - Added detailed statistics display
- **System improvements**:
  - Enhanced Windows compatibility
  - Added multiple fallback methods for admin operations
  - Improved Steam path detection
  - Added support for multiple Steam libraries

### v1.1.1 (2024-03-20)

- **Simplified sound system**:
  - Removed advanced audio processing
  - Streamlined sound configuration
  - Simplified to basic WAV file replacement
  - Cleaned up backup settings
  - Fixed sound enable/disable consistency

### v1.1.0 (2024-03-19)

- **Major feature update**:
  - Added configuration system
  - Added quality settings
  - Added backup system
  - Added logging system
  - Added GUI interface
  - Added quality and performance settings
  - Added workshop integration
  - Added texture caching
  - Added progress tracking
  - Added error recovery
  - Added space management for backups

### v1.0.0 (2024-03-19)

- **Initial release**
  - Added comprehensive README
  - Added version control
  - Implemented core features:
    - Weapon colorization
    - Transparency effects
    - Custom sounds
    - Automatic backups
    - Workshop content processing

## License

This software is provided as-is, without any warranties or conditions of any kind.
