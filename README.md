# Texture Extractor v1.3.7

A tool to extract and modify Garry's Mod textures.

## Features

- Extracts textures from Source Engine games (GMod, CS:S, HL2, etc.)
- Advanced SWEP detection with gamemode-specific classification (TTT, DarkRP, Sandbox, Zombie Survival, Murder, Prop Hunt)
- Extracts detailed SWEP metadata (PrintName, base class, category, gamemode, registration method)
- Robust error handling and GUI stability improvements
- Scans Lua files for model and texture references
- Decodes Lua cache files (.lc) and Garry's Mod cache files using LZMA decompression
- Generates VMT files for extracted textures
- Supports custom output paths
- Modern GUI with progress tracking and real-time scan task display
- Enhanced SWEP weapon VMT generation with category-based coloring and glow
- Improved memory and CPU usage monitoring
- Dependency management with automatic package installation
- Includes standalone tools for Lua cache decompression
- Automatic updates from GitHub repository

## Requirements

- Windows operating system
- Python 3.8 or higher
- Source Engine game installation (e.g., Garry's Mod)
- Required Python packages (automatically installed):
  - pillow: Image processing
  - psutil: System monitoring
  - vpk: VPK file handling
  - pywin32: Windows API access

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

### Standalone Tools

#### Lua Cache Decompressor

A standalone tool is included to decompress Garry's Mod Lua cache files:

```bash
python tools/gmod_lua_cache_decompressor.py "C:\Path\To\GarrysMod\garrysmod\cache\lua"
```

This will create a `decompressed` folder with all the decompressed Lua files.

#### SWEP Analyzer

A standalone tool for comprehensive SWEP detection and analysis:

```bash
python swep_analyzer.py
```

Features:
- Scans all Lua files in Garry's Mod directories (including addons, cache, workshop)
- Detects SWEPs from multiple gamemodes (TTT, DarkRP, Sandbox, Zombie Survival, Murder, Prop Hunt)
- Handles binary Lua files through decode-first approach
- Outputs detailed JSON report with gamemode and base class breakdowns

## Auto-Update System

The application includes an automatic update system that checks for new versions on GitHub:

- Automatically checks for updates at startup
- Downloads and applies updates with user permission
- Creates backups before applying updates
- Shows detailed progress during updates

## Version History

### v1.3.7 (2025-04-25)
- Fixed version number display in update notifications
- Improved version number extraction from GitHub releases
- Enhanced batch file with better directory handling
- Added additional error handling for update process

### v1.3.6 (2025-04-25)
- Completely overhauled the update system for improved reliability
- Added direct ZIP file version verification for more accurate update detection
- Improved file integrity checking during updates
- Enhanced error handling for file locks during the update process
- Added post-update completion system to handle locked files
- Improved Windows restart mechanism for smoother updates
- Fixed issues with GitHub version detection
- Added robust version number extraction from various formats
- Fixed batch file to properly handle application directory
- Improved update notification formatting

### v1.3.5 (2025-04-24)
- Added detailed module statistics tracking in a new "Modules" tab
- Added real-time performance metrics for SWEP detection and texture extraction
- Added memory and CPU usage monitoring
- Added visual indicators for module status (active/disabled)
- Added module-specific timing information

### v1.3.4 (2025-04-24)
- Added module settings to enable/disable specific components
- Added option to bypass SWEP detection module for improved performance
- Added option to disable texture extraction module
- Enhanced settings dialog with module configuration section

### v1.3.3 (2025-04-24)
- Fixed material folder structure handling to ensure proper merging
- Prevented creation of nested materials folders
- Improved path handling for texture extraction

### v1.3.2 (2025-04-24)
- Hotfix for stability issues in the SWEP detector module
- Improved error handling for edge cases
- Fixed potential memory leaks in texture processing

### v1.3.1 (2025-04-24)
- Fixed indentation issues in SWEP detector module that were breaking the GUI
- Improved error handling in binary Lua file processing
- Enhanced SWEP table parsing with more robust pattern matching

### v1.3.0 (2025-04-24)
- Added advanced SWEP detection with gamemode-specific classification
- Added support for multiple gamemodes (TTT, DarkRP, Sandbox, Zombie Survival, Murder, Prop Hunt)
- Added detailed SWEP metadata extraction
- Added standalone SWEP analyzer tool with comprehensive reporting
- Improved binary Lua file handling with decode-first approach
- Added parallel file processing for better performance

### v1.2.5 (2025-03-15)
- Added auto-update system with GitHub integration
- Added version comparison and download functionality
- Fixed window size and positioning issues
- Fixed error handling for missing files
- Added manual "Check for Updates" button in the settings dialog
- Enhanced update notification system with detailed status messages
- Improved error handling and robustness in the update process
- Fixed issue with version detection in the update service
- Added configuration options for controlling update behavior

### v1.2.0 (2025-02-28)
- Added Lua cache file decompression
- Added basic SWEP detection
- Added model and texture reference extraction
- Fixed VMT generation for special texture types
- Fixed progress tracking for large file sets

### v1.2.4 (2025-03-10)
- Enhanced SWEP detection with expanded directory list and weapon prefixes
- Added comprehensive weapon prefix list with hundreds of specific weapon models and types
- Added case-insensitive matching for directory and prefix detection
- Improved binary pattern matching with larger buffer size
- Added support for more file types in SWEP detection

### v1.2.3 (2025-03-01)
- Added LZMA decompression support for Garry's Mod Lua cache files
- Added standalone Lua cache decompression tool in the tools folder
- Added detailed step-by-step debugging with timestamps and thread IDs
- Added timeouts and limits for regex pattern matching to prevent freezing
- Improved error handling with detailed stack traces

### v1.2.2 (2025-02-20)
- **Robust Lua Cache Detection**:
  - Completely overhauled Lua cache file detection system
  - Added automatic detection of cache directories across multiple Steam library locations
  - Implemented multi-format processing for all cache files (binary, Lua cache, plain text)
  - Added comprehensive scanning of all files in cache directories (12,500+ files processed)
  - Added specific scanning of workshop and lua subdirectories in the cache
  - Implemented fallback paths for different Steam library configurations
  - Fixed issues with Lua cache decoder reference
  - Added dedicated methods for texture and model reference extraction
  - Enhanced error handling and logging for cache file processing
  - Added binary pattern matching for encoded cache files

### v1.2.1 (2025-02-15)

- **UI Improvements**:
  - Modernized the GUI with a more beautiful and user-friendly interface
  - Added custom application icon throughout the interface
  - Improved button styling with consistent colors
  - Fixed window sizing and layout issues (950x950 non-resizable)
  - Added proper padding around all elements
  - Made window non-resizable to maintain layout integrity
  - Rebuilt statistics panel with proper alignment
  - Reorganized deletion settings to group checkboxes together
  - Set trees and props deletion to be off by default
  - Added setting for specifying C4 sound replacement file
  - Added helpful sound file suggestions
  - Fixed BooleanVar handling for more reliable settings

### v1.2.0 (2025-02-01)

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

### v1.1.3 (2025-01-15)

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

### v1.1.2 (2025-01-05)

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

### v1.1.1 (2024-12-20)

- **Simplified sound system**:
  - Removed advanced audio processing
  - Streamlined sound configuration
  - Simplified to basic WAV file replacement
  - Cleaned up backup settings
  - Fixed sound enable/disable consistency

### v1.1.0 (2024-12-10)

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

### v1.0.0 (2024-12-01)

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
