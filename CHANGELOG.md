# Changelog

All notable changes to this project will be documented in this file.

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
