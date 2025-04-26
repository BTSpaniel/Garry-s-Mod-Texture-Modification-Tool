# Changelog

All notable changes to this project will be documented in this file.

## [1.3.9] - 2025-04-26

### Fixed
- Fixed update service incorrectly detecting new versions when none are available
- Improved version comparison logic to prevent false update notifications
- Updated fallback version handling to use current version instead of hardcoded value

## [1.3.8] - 2025-04-26

### Added
- Modularized SWEP detector architecture for better maintainability and extensibility
- Enhanced texture reference extraction with more comprehensive pattern matching
- Improved model reference detection with path normalization
- Better gamemode detection for various SWEP types

### Fixed
- Improved compatibility with custom and base weapons
- Enhanced SWEP table parsing for ViewModel, WorldModel, and custom materials
- Fixed path handling for texture and model references
- Improved detection of material paths in various formats

## [1.3.7] - 2025-04-25

### Fixed
- Fixed version number display in update notifications
- Improved version number extraction from GitHub releases
- Enhanced batch file with better directory handling
- Added additional error handling for update process

## [1.3.6] - 2025-04-25

### Added
- Enhanced SWEP weapon VMT generation with category-based coloring and glow
- Improved real-time scan task display showing task completion and VPK discovery
- Centralized status information in the progress bar section
- Dependency management with automatic package installation from requirements.txt
- Improved memory and CPU usage monitoring with per-core percentage display

### Fixed
- Fixed module settings not being properly saved and applied
- Fixed deletion settings not being correctly saved
- Removed redundant UI elements for cleaner interface
- Improved error handling in system monitoring

## [1.3.5] - 2025-04-24

### Added
- New "Modules" tab in the statistics section for detailed module tracking
- Real-time performance metrics for SWEP detection and texture extraction
- Memory and CPU usage monitoring (requires psutil package)
- Visual indicators for module status (active/disabled)
- Module-specific timing information to track processing duration
- Enhanced UI feedback for module performance

## [1.3.4] - 2025-04-24

### Added
- Module settings to enable/disable specific components
- Option to bypass SWEP detection module for improved performance
- Option to disable texture extraction module
- Enhanced settings dialog with module configuration section

## [1.3.3] - 2025-04-24

### Fixed
- Fixed material folder structure handling to ensure proper merging
- Prevented creation of nested materials folders
- Improved path handling for texture extraction
- Enhanced VMT path processing to strip 'materials/' prefix

## [1.3.2] - 2025-04-24

### Fixed
- Hotfix for stability issues in the SWEP detector module
- Improved error handling for edge cases
- Fixed potential memory leaks in texture processing
- Ensured proper initialization of model and texture references

## [1.3.1] - 2025-04-24

### Fixed
- Fixed indentation issues in SWEP detector module that were breaking the GUI
- Improved error handling in binary Lua file processing
- Enhanced SWEP table parsing with more robust pattern matching

## [1.3.0] - 2025-04-24

### Added
- Advanced SWEP detection with gamemode-specific classification
- Support for multiple gamemodes (TTT, DarkRP, Sandbox, Zombie Survival, Murder, Prop Hunt)
- Detailed SWEP metadata extraction (PrintName, base class, category, gamemode, registration method)
- Standalone SWEP analyzer tool with comprehensive reporting
- Improved binary Lua file handling with decode-first approach
- Parallel file processing for better performance

### Fixed
- Indentation and parsing errors in SWEP detector module
- Binary content processing in SWEP detector
- Improved texture and model reference extraction

## [1.2.5] - 2025-03-15

### Added
- Auto-update system with GitHub integration
- Version comparison and download functionality

### Fixed
- Window size and positioning issues
- Error handling for missing files

## [1.2.0] - 2025-02-28

### Added
- Lua cache file decompression
- SWEP detection (basic)
- Model and texture reference extraction

### Fixed
- VMT generation for special texture types
- Progress tracking for large file sets

## [1.1.0] - 2025-01-15

### Added
- Modern GUI with progress tracking
- Custom output path selection
- VMT file generation

## [1.0.0] - 2024-12-01

### Added
- Initial release
- Basic texture extraction from Source Engine games
- Support for Garry's Mod file formats
