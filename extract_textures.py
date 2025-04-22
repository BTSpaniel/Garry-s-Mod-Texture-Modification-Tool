# =============================================================================
# Texture Extractor v1.1.3
# A tool to extract and modify Garry's Mod textures
# =============================================================================

"""
=== Texture Extractor v1.1.3 ===
A tool to extract and modify Garry's Mod textures.

=== CHANGELOG ===

v1.1.3 (2024-03-21)
- Added settings system:
  * Added comprehensive settings dialog
  * Added texture processing settings
  * Added backup configuration
  * Added transparency controls
  * Added performance tuning
  * Added logging configuration
  * Added real-time settings validation
  * Added settings persistence
- GUI improvements:
  * Added settings button
  * Improved button layout
  * Enhanced user feedback
  * Added input validation

v1.1.2 (2024-03-21)
- Enhanced error handling:
  * Improved permission handling for file operations
  * Added robust directory creation with multiple fallback methods
  * Enhanced backup verification system
  * Added detailed logging for troubleshooting
  * Improved GUI error reporting
- Improved file processing:
  * Added sanitization for file paths
  * Enhanced VPK file handling
  * Added support for more file formats
  * Optimized texture processing
- GUI improvements:
  * Added real-time progress updates
  * Enhanced status reporting
  * Improved error visualization
  * Added detailed statistics display
- System improvements:
  * Enhanced Windows compatibility
  * Added multiple fallback methods for admin operations
  * Improved Steam path detection
  * Added support for multiple Steam libraries

v1.1.1 (2024-03-20)
- Simplified sound system:
  * Removed advanced audio processing
  * Streamlined sound configuration
  * Simplified to basic WAV file replacement
  * Cleaned up backup settings
  * Fixed sound enable/disable consistency

v1.1.0 (2024-03-19)
- Major feature update:
  * Added configuration system
  * Added quality settings
  * Added backup system
  * Added logging system
  * Added GUI interface
  * Added quality and performance settings
  * Added workshop integration
  * Added texture caching
  * Added progress tracking
  * Added error recovery
  * Added space management for backups

v1.0.0 (2024-03-19)
- Initial release
- Added comprehensive README
- Added version control
- Implemented core features:
  * Weapon colorization
  * Transparency effects
  * Custom sounds
  * Automatic backups
  * Workshop content processing

=== END README ===
"""

# Core imports that are always available
import sys
import subprocess
import os
import string
import struct
import mmap
from pathlib import Path
import logging
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import shutil
import zipfile
import tarfile
from typing import Dict, List, Optional, Tuple, Union
import queue
import hashlib
import tempfile
import time
import traceback
from collections import defaultdict

# Optional GUI imports
try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

# Import VPK handling
try:
    import vpk
    HAS_VPK = True
    logging.info("VPK module loaded successfully")
except ImportError:
    HAS_VPK = False
    logging.warning("VPK module not found. VPK file processing will be disabled.")

# Initialize Windows-specific modules
try:
    import win32security
    import win32api
    import win32con
    import ntsecuritycon
    from win32com.shell import shell, shellcon
    HAS_WIN32 = True
    logging.info("Windows modules loaded successfully")
except ImportError:
    HAS_WIN32 = False
    win32security = None
    win32api = None
    win32con = None
    shell = None
    shellcon = None
    ntsecuritycon = None
    logging.warning("Windows modules not found. Some features will be disabled.")

def initialize_windows_imports():
    """Initialize Windows-specific imports after dependencies are installed."""
    global win32security, win32api, win32con, shell, shellcon, ntsecuritycon
    try:
        import win32security
        import win32api
        import win32con
        from win32com.shell import shell, shellcon
        import ntsecuritycon as con
        return True
    except ImportError as e:
        logging.error(f"Failed to import Windows modules: {e}")
        return False

# List of required packages with their pip install names
REQUIRED_PACKAGES = [
    ('vpk', 'vpk'),  # For VPK file handling
    ('shutil', None),         # Built-in, for file operations
    ('pathlib', 'pathlib'),   # For path handling
    ('struct', None),         # Built-in, for binary data
    ('mmap', None),           # Built-in, for memory mapping
    ('winreg', None),         # Built-in, for registry access
    ('win32security', 'pywin32'),  # For Windows security and admin features
    ('win32api', 'pywin32'),      # For Windows API access
    ('win32con', 'pywin32'),      # For Windows constants
    ('win32com', 'pywin32')       # For COM interface
]

def check_admin():
    """Check if the script has administrator privileges."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def request_admin():
    """Show a message box requesting admin privileges."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        result = messagebox.askyesno(
            "Administrator Privileges Required",
            "This script needs administrator privileges to modify files in the Garry's Mod directory.\n\n" +
            "Would you like to restart the script with administrator privileges?",
            icon='warning'
        )
        
        root.destroy()
        return result
    except:
        # If tkinter fails, fall back to console input
        print("\nAdministrator privileges are required.")
        response = input("Would you like to restart with administrator privileges? (y/n): ").lower()
        return response.startswith('y')

def elevate_script():
    """Restart the script with admin privileges."""
    try:
        import sys
        import ctypes
        import subprocess
        import os
        
        if ctypes.windll.shell32.IsUserAnAdmin():
            return True
            
        # Get absolute path to the script
        script_path = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script_path)
        
        if getattr(sys, 'frozen', False):
            # If we're running as a compiled executable
            args = [script_path] + sys.argv[1:]
        else:
            # If we're running as a Python script
            args = [sys.executable, script_path] + sys.argv[1:]
        
        # Create a command that will:
        # 1. Change to the correct directory
        # 2. Run the script
        # 3. Keep the window open
        cmd_args = ' '.join(f'"{arg}"' for arg in args)
        cmd = f'cd /d "{script_dir}" && {cmd_args}'
        
        # Use ShellExecuteW for UAC elevation
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            f"/K {cmd}",
            script_dir,  # Set working directory
            1  # SW_SHOWNORMAL
        )
        
        if result <= 32:  # Error codes are <= 32
            raise Exception(f"Failed to elevate privileges. Error code: {result}")
            
        sys.exit(0)  # Exit current instance
        
    except Exception as e:
        logging.error(f"Failed to elevate privileges: {e}")
        return False

# =============================================================================
# ===== CONFIGURATION OPTIONS =====
# =============================================================================

# -----------------------------------------------------------------------------
# Version Information
# -----------------------------------------------------------------------------
VERSION = "1.1.3"
VERSION_DATE = "2024-03-21"

# -----------------------------------------------------------------------------
# Basic Options
# -----------------------------------------------------------------------------

# Core Features
SKIP_DEPENDENCIES = False    # Set to False to enable automatic dependency installation
ENABLE_WEAPON_COLORS = True  # Set to False to disable all weapon coloring
ENABLE_TRANSPARENCY = True   # Set to False to disable transparency for non-weapon items
ENABLE_CUSTOM_SOUNDS = True  # Set to False to disable custom sound creation

# New Processing Options
ENABLE_PARALLEL_PROCESSING = True  # Enable multi-threaded processing
MAX_THREADS = 4                    # Maximum number of parallel threads
ENABLE_MEMORY_OPTIMIZATION = True  # Enable memory usage optimization
CHUNK_SIZE = 1024 * 1024          # Chunk size for file reading (1MB)

# -----------------------------------------------------------------------------
# Quality and Performance Settings
# -----------------------------------------------------------------------------

# Texture Processing
TEXTURE_QUALITY = {
    'compress_textures': True,     # Enable texture compression
    'max_texture_size': 2048,      # Maximum texture dimension
    'mipmap_generation': True,     # Generate mipmaps for textures
    'texture_format': 'DXT5',      # DXT1, DXT3, DXT5
    'quality_level': 'high'        # low, medium, high, ultra
}

# Performance Settings
PERFORMANCE = {
    'cache_enabled': True,         # Enable file caching
    'cache_size': 512,            # Cache size in MB
    'preload_textures': True,     # Preload textures into memory
    'batch_processing': True,     # Process files in batches
    'batch_size': 100            # Number of files per batch
}

# -----------------------------------------------------------------------------
# Backup Settings
# -----------------------------------------------------------------------------

BACKUP = {
    'enabled': True,          # Master switch for backup creation
    'location': None,        # Custom backup location (None = default)
    'max_backups': 5,        # Maximum number of backups to keep
    'compression': True,     # Use compression for backups
    'include_cfg': True,     # Include configuration files
    'include_materials': True # Include material files
}

# -----------------------------------------------------------------------------
# Transparency Settings
# -----------------------------------------------------------------------------

# Enhanced transparency configuration
TRANSPARENCY = {
    'default_alpha': 0.85,        # Default transparency value
    'weapon_alpha': 1.0,          # Transparency for weapons
    'effect_alpha': 0.5,          # Transparency for effects
    'prop_alpha': 0.75,          # Transparency for props
    'enable_fade': True,          # Enable distance-based fade
    'fade_start': 500,           # Distance to start fading
    'fade_end': 1000            # Distance for full fade
}

# -----------------------------------------------------------------------------
# Sound Settings
# -----------------------------------------------------------------------------

SOUND = {
    'enable_custom_sounds': True,  # Master switch for custom sounds
    
    # C4 sound configuration
    'c4_sounds': {
        'plant': {
            'enabled': True,
            'sound_type': 'scream',  # 'scream', 'beep', or 'custom'
            'custom_path': None,     # Path to custom WAV file
            'volume': '1.0',
            'pitch': '100'
        },
        'beep': {
            'enabled': True,
            'sound_type': 'scream',
            'custom_path': None,
            'volume': '1.0',
            'pitch': '100'
        },
        'explode': {
            'enabled': True,
            'sound_type': 'scream',
            'custom_path': None,
            'volume': '1.0',
            'pitch': '100'
        }
    },
    
    # Available sound types
    'sound_types': {
        'scream': {
            'male01': 'vo/npc/male01/pain07.wav',
            'male02': 'vo/npc/male01/pain08.wav',
            'female01': 'vo/npc/female01/pain07.wav',
            'zombie': 'npc/zombie/zombie_pain6.wav',
            'headcrab': 'npc/headcrab/pain1.wav',
            'combine': 'npc/combine_soldier/pain3.wav'
        },
        'beep': {
            'normal': 'buttons/button17.wav',
            'danger': 'buttons/blip1.wav',
            'warning': 'buttons/blip2.wav'
        },
        'custom': {}  # Will be populated with user's custom sounds
    },
    
    # Basic settings
    'backup_original_sounds': True,  # Create backup of original sounds
    'restore_on_exit': False        # Restore original sounds when done
}

# -----------------------------------------------------------------------------
# Workshop Integration
# -----------------------------------------------------------------------------

WORKSHOP = {
    'process_workshop': True,     # Process workshop content
    'auto_update': True,         # Auto-update workshop items
    'download_missing': True,     # Download missing workshop content
    'verify_files': True,        # Verify workshop file integrity
    'max_workshop_size': 2048,   # Maximum workshop file size (MB)
    'workshop_cache': True       # Enable workshop content caching
}

# -----------------------------------------------------------------------------
# Logging and Debug
# -----------------------------------------------------------------------------

LOGGING = {
    'log_level': 'INFO',         # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'log_to_file': True,         # Save logs to file
    'log_format': 'detailed',    # basic, detailed, debug
    'max_log_size': 10,         # Maximum log file size (MB)
    'max_log_files': 5,         # Maximum number of log files to keep
    'log_location': None        # Custom log location (None = default)
}

# -----------------------------------------------------------------------------
# GUI Settings
# -----------------------------------------------------------------------------

# Update GUI settings to use default theme
GUI = {
    'enable_gui': True,         # Enable GUI interface
    'theme': 'default',        # Use system default theme
    'show_preview': True,      # Show texture previews
    'window_size': '800x600',  # Default window size
    'font_size': 10           # Default font size
}

# -----------------------------------------------------------------------------
# Weapon Color Categories
# -----------------------------------------------------------------------------

# Detailed weapon color coding options
WEAPON_COLORS = {
    'pistol': {
        'enabled': True,
        'color': '[1 0 0]',  # Red
        'name': 'Red',
        'patterns': [
            # Basic patterns
            'pistol', 'glock', 'usp', 'deagle', 'revolver', '357', 'p228', 'p250', 'magnum', 'fiveseven', 'elite',
            # TTT specific
            'ttt_pistol', 'ttt_glock', 'ttt_deagle', 'ttt_revolver', 'weapon_ttt_glock', 'weapon_zm_pistol', 'weapon_zm_revolver',
            # View/World/Client models
            'v_pistol', 'v_glock', 'v_usp', 'v_deagle', 'v_revolver', 'v_357', 'v_p228', 'v_p250',
            'w_pistol', 'w_glock', 'w_usp', 'w_deagle', 'w_revolver', 'w_357', 'w_p228', 'w_p250',
            'c_pistol', 'c_glock', 'c_usp', 'c_deagle', 'c_revolver', 'c_357', 'c_p228', 'c_p250',
            # Case variations
            'PISTOL', 'GLOCK', 'USP', 'DEAGLE', 'REVOLVER', '357', 'P228', 'P250', 'FIVESEVEN', 'ELITE'
        ]
    },
    'rifle': {
        'enabled': True,
        'color': '[0 1 0]',  # Green
        'name': 'Green',
        'patterns': [
            # Basic patterns
            'rifle', 'ak47', 'm4a1', 'famas', 'galil', 'aug', 'sg552', 'awp', 'scout', 'sniper', 'assault', 'carbine',
            'g3sg1', 'sg550', 'hunting_rifle', 'sniper_military',
            # TTT specific
            'ttt_rifle', 'ttt_ak47', 'ttt_m4a1', 'ttt_awp', 'ttt_scout', 'weapon_ttt_m16',
            # View/World/Client models
            'v_rifle', 'v_ak47', 'v_m4a1', 'v_famas', 'v_galil', 'v_aug', 'v_sg552', 'v_awp', 'v_scout',
            'w_rifle', 'w_ak47', 'w_m4a1', 'w_famas', 'w_galil', 'w_aug', 'w_sg552', 'w_awp', 'w_scout',
            'c_rifle', 'c_ak47', 'c_m4a1', 'c_famas', 'c_galil', 'c_aug', 'c_sg552', 'c_awp', 'c_scout',
            # Case variations
            'RIFLE', 'AK47', 'M4A1', 'FAMAS', 'GALIL', 'AUG', 'SG552', 'AWP', 'SCOUT', 'SNIPER', 'ASSAULT', 'CARBINE'
        ]
    },
    'smg': {
        'enabled': True,
        'color': '[0 0 1]',  # Blue
        'name': 'Blue',
        'patterns': [
            # Basic patterns
            'smg', 'mp5', 'mp7', 'mac10', 'ump45', 'p90', 'tmp', 'mp5navy',
            # HL2 specific
            'hl2_smg', 'hl2/smg', 'hl2/weapons/smg', 'hl2/weapons/hl2_smg',
            'pulse_rifle', 'pulserifle', 'pulse', 'pulse/rifle', 'pulse/weapons/pulse_rifle',
            # TTT specific
            'ttt_smg', 'ttt_mp5', 'ttt_mac10', 'ttt_ump45', 'weapon_zm_mac10',
            # View/World/Client models
            'v_hl2_smg', 'v_pulse_rifle', 'w_hl2_smg', 'w_pulse_rifle',
            'c_hl2_smg', 'c_pulse_rifle',
            # Additional variations
            'smg1', 'hl2_smg1', 'ar2', 'pulse',
            'v_smg1', 'v_hl2_smg1', 'v_ar2',
            'w_smg1', 'w_hl2_smg1', 'w_ar2',
            'c_smg1', 'c_hl2_smg1', 'c_ar2',
            # Case variations
            'SMG', 'HL2_SMG', 'PULSE_RIFLE', 'AR2', 'MP5', 'MAC10', 'UMP45', 'P90', 'TMP', 'MP5NAVY'
        ]
    },
    'shotgun': {
        'enabled': True,
        'color': '[1 0 1]',  # Purple
        'name': 'Purple',
        'patterns': [
            # Basic patterns
            'shotgun', 'nova', 'mag7', 'sawedoff', 'xm1014', 'spas', 'pump', 'm3', 'autoshotgun', 'pumpshotgun',
            'shotgun_spas',
            # TTT specific
            'ttt_shotgun', 'ttt_nova', 'ttt_sawedoff', 'ttt_pump', 'weapon_zm_shotgun',
            # View/World/Client models
            'v_shotgun', 'v_nova', 'v_mag7', 'v_sawedoff', 'v_xm1014', 'v_spas', 'v_pump', 'v_m3',
            'w_shotgun', 'w_nova', 'w_mag7', 'w_sawedoff', 'w_xm1014', 'w_spas', 'w_pump', 'w_m3',
            'c_shotgun', 'c_nova', 'c_mag7', 'c_sawedoff', 'c_xm1014', 'c_spas', 'c_pump', 'c_m3',
            # Case variations
            'SHOTGUN', 'NOVA', 'MAG7', 'SAWEDOFF', 'XM1014', 'SPAS', 'PUMP', 'M3', 'AUTOSHOTGUN', 'PUMPSHOTGUN'
        ]
    },
    'crossbow': {
        'enabled': True,
        'color': '[1 0.5 0.5]',  # Pink
        'name': 'Pink',
        'patterns': [
            # Basic patterns
            'crossbow', 'bow', 'arrow',
            # TTT specific
            'ttt_crossbow', 'ttt_bow',
            # View/World/Client models
            'v_crossbow', 'v_bow',
            'w_crossbow', 'w_bow',
            'c_crossbow', 'c_bow',
            # Case variations
            'CROSSBOW', 'BOW', 'ARROW'
        ]
    },
    'explosive': {
        'enabled': True,
        'color': '[1 0.5 0]',  # Orange
        'name': 'Orange',
        'patterns': [
            # Basic patterns
            'grenade', 'explosive', 'c4', 'rpg', 'missile', 'bomb', 'mine', 'dynamite', 'tnt', 'frag', 'slam',
            'flashbang', 'hegrenade', 'smokegrenade', 'molotov', 'pipe_bomb', 'grenade_launcher',
            # TTT specific
            'ttt_c4', 'ttt_bomb', 'ttt_explosive', 'ttt_grenade', 'ttt_mine', 'weapon_ttt_c4', 'weapon_ttt_turtlenade',
            'weapon_ttt_tripmine', 'weapon_ttt_decoy', 'weapon_ttt_flaregun',
            # View/World/Client models
            'v_grenade', 'v_c4', 'v_rpg', 'v_missile', 'v_bomb', 'v_mine', 'v_frag', 'v_slam',
            'w_grenade', 'w_c4', 'w_rpg', 'w_missile', 'w_bomb', 'w_mine', 'w_frag', 'w_slam',
            'c_grenade', 'c_c4', 'c_rpg', 'c_missile', 'c_bomb', 'c_mine', 'c_frag', 'c_slam',
            # Case variations
            'GRENADE', 'EXPLOSIVE', 'C4', 'RPG', 'MISSILE', 'BOMB', 'MINE', 'DYNAMITE', 'TNT', 'FRAG', 'SLAM'
        ]
    },
    'medical': {
        'enabled': True,
        'color': '[0 1 1]',  # Cyan
        'name': 'Cyan',
        'patterns': [
            # Basic patterns
            'medkit', 'defibrillator', 'health', 'heal', 'bandage', 'first_aid', 'pain_pills', 'adrenaline',
            # TTT specific
            'weapon_ttt_health_station', 'weapon_medkit', 'weapon_defibrillator',
            # View/World/Client models
            'v_medkit', 'v_defibrillator', 'v_health', 'v_heal', 'v_bandage', 'v_first_aid',
            'w_medkit', 'w_defibrillator', 'w_health', 'w_heal', 'w_bandage', 'w_first_aid',
            'c_medkit', 'c_defibrillator', 'c_health', 'c_heal', 'c_bandage', 'c_first_aid',
            # Case variations
            'MEDKIT', 'DEFIBRILLATOR', 'HEALTH', 'HEAL', 'BANDAGE', 'FIRST_AID', 'PAIN_PILLS', 'ADRENALINE'
        ]
    },
    'utility': {
        'enabled': True,
        'color': '[1 1 0]',  # Yellow
        'name': 'Yellow',
        'patterns': [
            # Basic patterns
            'tool', 'camera', 'keys', 'lockpick', 'keypad', 'atm', 'card', 'checker', 'pocket',
            # TTT specific
            'weapon_ttt_radio', 'weapon_ttt_binoculars', 'weapon_ttt_teleport', 'ttt_weapon_random',
            # DarkRP specific
            'weapon_arc_atmcard', 'weaponchecker', 'pocket', 'keys', 'lockpick', 'keypad_cracker',
            # View/World/Client models
            'v_tool', 'v_camera', 'v_keys', 'v_lockpick', 'v_keypad', 'v_atm', 'v_card', 'v_checker', 'v_pocket',
            'w_tool', 'w_camera', 'w_keys', 'w_lockpick', 'w_keypad', 'w_atm', 'w_card', 'w_checker', 'w_pocket',
            'c_tool', 'c_camera', 'c_keys', 'c_lockpick', 'c_keypad', 'c_atm', 'c_card', 'c_checker', 'c_pocket',
            # Case variations
            'TOOL', 'CAMERA', 'KEYS', 'LOCKPICK', 'KEYPAD', 'ATM', 'CARD', 'CHECKER', 'POCKET'
        ]
    },
    'special': {
        'enabled': True,
        'color': '[0 1 1]',  # Cyan
        'name': 'Cyan',
        'patterns': [
            # Basic patterns
            'gravity', 'physcannon', 'physgun', 'toolgun', 'tool', 'stunstick', 'stun', 'taser', 'crowbar', 'bat', 
            'baseball', 'knife', 'sword', 'blade', 'melee', 'bugbait', 'annabelle', 'alyxgun', 'gmod_tool', 'gmod_camera',
            'first_aid_kit', 'defibrillator', 'pain_pills', 'adrenaline', 'gascan', 'fireaxe', 'crowbar_l4d2',
            'golfclub', 'cricket_bat', 'frying_pan', 'machete', 'tonfa', 'chainsaw', 'm60',
            # TTT specific
            'ttt_knife', 'ttt_sword', 'ttt_bat', 'ttt_crowbar', 'ttt_toolgun', 'ttt_physgun', 'weapon_ttt_knife',
            'weapon_ttt_phammer', 'weapon_ttt_push', 'weapon_mu_knife', 'murderdoorlocker', 'weapon_striderbuster',
            'weapon_handcuffs', 'unarrest_stick', 'arrest_stick', 'weapon_cuff_police',
            # DarkRP specific
            'darkrp_money', 'darkrp_lockpick', 'darkrp_keycard', 'darkrp_medkit', 'darkrp_radio',
            # Sandbox specific
            'sandbox_tool', 'sandbox_physgun', 'sandbox_spawner',
            # Murder specific
            'murder_knife', 'murder_gun', 'murder_pistol', 'murder_shotgun',
            # Zombie specific
            'zombie_knife', 'zombie_gun', 'zombie_pistol', 'zombie_shotgun',
            # Prop Hunt specific
            'prop_hunt_knife', 'prop_hunt_gun', 'prop_hunt_pistol',
            # View/World/Client models
            'v_gravity', 'v_physcannon', 'v_physgun', 'v_toolgun', 'v_stunstick', 'v_knife', 'v_sword', 'v_crowbar', 'v_bat',
            'w_gravity', 'w_physcannon', 'w_physgun', 'w_toolgun', 'w_stunstick', 'w_knife', 'w_sword', 'w_crowbar', 'w_bat',
            'c_gravity', 'c_physcannon', 'c_physgun', 'c_toolgun', 'c_stunstick', 'c_knife', 'c_sword', 'c_crowbar', 'c_bat',
            # Case variations
            'GRAVITY', 'PHYSCANNON', 'PHYSGUN', 'TOOLGUN', 'TOOL', 'STUNSTICK', 'STUN', 'TASER', 'CROWBAR', 'BAT'
        ]
    }
}

# =============================================================================
# ===== END CONFIGURATION =====
# =============================================================================

class ProgressTracker:
    """Track progress of operations with a simple counter."""
    def __init__(self, total, description=""):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        
    def update(self, amount=1):
        """Update progress counter."""
        self.current += amount
        if self.current % 10 == 0 or self.current == self.total:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed if elapsed > 0 else 0
            logging.info(f"{self.description}: {self.current}/{self.total} ({rate:.1f}/s)")

def process_vpk_file(file_path: Path) -> List[str]:
    """Process a VPK file and extract texture information."""
    global HAS_VPK
    
    try:
        if not file_path.exists():
            logging.error(f"File not found: {file_path}")
            return []
            
        if not HAS_VPK:
            logging.error("VPK module not available. Cannot process VPK files.")
            return []
            
        # Only process _dir.vpk files, skip numbered VPK files
        if not file_path.name.endswith('_dir.vpk'):
            logging.debug(f"Skipping non-directory VPK file: {file_path}")
            return []
            
        # Initialize VPK package with error handling
        try:
            vpk_package = vpk.open(str(file_path))
            if not vpk_package:
                logging.error(f"Failed to open VPK file (empty package): {file_path}")
                return []
        except vpk.VPKError as e:
            logging.error(f"VPK error processing {file_path}: {e}")
            return []
        except Exception as e:
            logging.error(f"Failed to open VPK file {file_path}: {e}")
            return []
            
        texture_paths = []
        
        # Process each file in the VPK
        try:
            for file_path in vpk_package:
                try:
                    # Check if it's a texture file
                    if file_path.lower().endswith('.vtf') and 'materials/' in file_path.lower():
                        texture_paths.append(file_path)
                except Exception as e:
                    logging.debug(f"Error processing file {file_path} in VPK: {e}")
                    continue
        except Exception as e:
            logging.error(f"Error iterating VPK contents {file_path}: {e}")
            return []
                
        return texture_paths
        
    except Exception as e:
        logging.error(f"Error processing VPK file {file_path}: {e}")
        return []

def process_bsp_file(file_path: Path) -> List[str]:
    """Process a BSP file and extract embedded textures."""
    try:
        if not file_path.exists():
            logging.error(f"File not found: {file_path}")
            return []
            
        texture_paths = []
        
        # Read BSP file in chunks
        with open(file_path, 'rb') as f:
            # Read BSP header
            header = f.read(8)  # BSP header is typically 8 bytes
            
            # Check for different BSP versions
            header_ident = header[:4]
            if header_ident not in [b'VBSP', b'IBSP', b'RBSP']:
                logging.warning(f"Unknown BSP version identifier {header_ident} in {file_path}")
                return []
                
            version = struct.unpack('I', header[4:8])[0]
            logging.debug(f"BSP version: {version} for {file_path}")
            
            # Skip to lump directory
            f.seek(8)
            
            # Read texture lump (lump 2 in Source engine)
            texture_lump_offset = struct.unpack('I', f.read(4))[0]
            texture_lump_size = struct.unpack('I', f.read(4))[0]
            
            if texture_lump_size > 0:
                try:
                    f.seek(texture_lump_offset)
                    texture_data = f.read(texture_lump_size)
                    
                    # Process texture entries
                    offset = 0
                    while offset < len(texture_data):
                        try:
                            # Read texture name (null-terminated string)
                            name_end = texture_data.find(b'\0', offset)
                            if name_end == -1:
                                break
                                
                            name_bytes = texture_data[offset:name_end]
                            try:
                                name = name_bytes.decode('utf-8', errors='ignore').strip()
                                if name and name.lower().endswith('.vtf'):
                                    # Add materials/ prefix if not present
                                    if not name.lower().startswith('materials/'):
                                        name = f"materials/{name}"
                                    texture_paths.append(name)
                            except UnicodeDecodeError:
                                logging.debug(f"Skipping invalid texture name in {file_path}")
                                
                            # Move to next texture entry (128-byte alignment)
                            offset = (name_end + 128) & ~127
                            
                        except Exception as e:
                            logging.debug(f"Error processing texture entry in {file_path}: {e}")
                            offset += 128  # Skip to next potential entry
                            
                except Exception as e:
                    logging.error(f"Error reading texture lump in {file_path}: {e}")
                    
        return texture_paths
        
    except Exception as e:
        logging.error(f"Error processing BSP file {file_path}: {e}")
        return []

def process_gma_file(file_path: Path) -> List[str]:
    """Process a GMA (Garry's Mod Addon) file and extract textures."""
    try:
        if not file_path.exists():
            logging.error(f"File not found: {file_path}")
            return []
            
        texture_paths = []
        
        # Read GMA file
        with open(file_path, 'rb') as f:
            # Check GMA header
            header = f.read(4)
            if header != b'GMAD':
                logging.error(f"Invalid GMA file format: {file_path}")
                return []
                
            # Skip version and SteamID
            f.seek(13)
            
            # Read file entries
            while True:
                # Read file path length
                path_length = f.read(1)[0]
                if path_length == 0:
                    break
                    
                # Read file path
                try:
                    file_path = f.read(path_length).decode('utf-8', errors='ignore')
                    
                    if file_path.lower().endswith('.vtf') and 'materials/' in file_path.lower():
                        texture_paths.append(file_path)
                except UnicodeDecodeError:
                    logging.debug(f"Skipping invalid file path in GMA")
                    
                # Skip file size and CRC
                f.seek(8, 1)
                    
        return texture_paths
        
    except Exception as e:
        logging.error(f"Error processing GMA file {file_path}: {e}")
        return []

def process_file(file_path: Path) -> List[str]:
    """Process a file based on its extension."""
    try:
        ext = file_path.suffix.lower()
        
        if ext == '.vpk':
            return process_vpk_file(file_path)
        elif ext == '.bsp':
            return process_bsp_file(file_path)
        elif ext == '.gma':
            return process_gma_file(file_path)
        else:
            logging.warning(f"Unsupported file type: {file_path}")
            return []
            
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
        return []

def create_vmt_content(vtf_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Create VMT content for a VTF texture."""
    try:
        # Remove 'materials/' from the start if present
        if vtf_path.lower().startswith('materials/'):
            vtf_path = vtf_path[len('materials/'):]
            
        # Get the base path without extension
        base_path = vtf_path[:-4] if vtf_path.lower().endswith('.vtf') else vtf_path
        
        # Determine texture type based on path
        texture_type = None
        for category, settings in WEAPON_COLORS.items():
            if settings['enabled']:
                for pattern in settings['patterns']:
                    if pattern.lower() in base_path.lower():
                        texture_type = category
                        break
                if texture_type:
                    break
                    
        # Create VMT content based on type
        if texture_type and WEAPON_COLORS[texture_type]['enabled']:
            # Weapon texture
            color = WEAPON_COLORS[texture_type]['color']
            return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
    "$color2" {color}
    "$translucent" "1"
    "$alpha" "{TRANSPARENCY['weapon_alpha']}"
}}''', texture_type)
        elif any(x in base_path.lower() for x in ['glass', 'window']):
            # Extra transparent texture
            return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
    "$translucent" "1"
    "$alpha" "{TRANSPARENCY['effect_alpha']}"
}}''', 'transparent')
        else:
            # All other textures - make them transparent by default
            return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
    "$translucent" "1"
    "$alpha" "{TRANSPARENCY['default_alpha']}"
}}''', 'normal')
            
    except Exception as e:
        logging.error(f"Error creating VMT content for {vtf_path}: {e}")
        return None, None

def setup_logging():
    """Initialize logging configuration."""
    try:
        # Create logs directory if it doesn't exist
        log_dir = Path(LOGGING['log_location'] or "logs")
        log_dir.mkdir(exist_ok=True)
        
        # Set up log file name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"texture_extractor_{timestamp}.log"

        # Custom filter to exclude detailed error messages
        class ErrorFilter(logging.Filter):
            def filter(self, record):
                # Filter out detailed syntax and linter errors
                msg = record.getMessage().lower()
                
                # Technical errors to filter
                technical_errors = [
                    'unexpected indent',
                    'unindent',
                    'indentation',
                    'syntax error',
                    'invalid syntax',
                    'expected expression',
                    'expected an indented block',
                    'inconsistent use of tabs',
                    'no attribute',
                    'attribute error',
                    'name error',
                    'type error',
                    'index error',
                    'key error',
                    'value error',
                    'assertion error',
                    'runtime error'
                ]
                
                # Only show user-friendly errors
                if record.levelno >= logging.ERROR:
                    # Convert technical errors to user-friendly messages
                    if any(err in msg for err in technical_errors):
                        return False  # Filter out technical errors
                    
                    # Keep user-friendly error messages
                    user_friendly = any(x in msg for x in [
                        'permission denied',
                        'access denied',
                        'file not found',
                        'directory not found',
                        'failed to create',
                        'could not open',
                        'error processing',
                        'error creating'
                    ])
                    return user_friendly
                    
                # For non-error messages, show progress and success messages
                return not any(err in msg for err in technical_errors)
        
        # Configure logging format based on settings
        if LOGGING['log_format'] == 'detailed':
            log_format = '%(message)s'  # Most basic format for users
        elif LOGGING['log_format'] == 'debug':
            log_format = '%(message)s'  # Most basic format for users
        else:  # basic
            log_format = '%(message)s'  # Most basic format for users
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOGGING['log_level']))
        
        # Clear any existing handlers
        root_logger.handlers = []
        
        # Create console handler with custom filter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        console_handler.addFilter(ErrorFilter())
        root_logger.addHandler(console_handler)
        
        # Create file handler if enabled (keeps detailed logs)
        if LOGGING['log_to_file']:
            file_handler = logging.FileHandler(log_file)
            detailed_format = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            file_handler.setFormatter(logging.Formatter(detailed_format))
            root_logger.addHandler(file_handler)
        
        # Rotate old log files if needed
        if LOGGING['log_to_file']:
            log_files = sorted(log_dir.glob('texture_extractor_*.log'))
            while len(log_files) > LOGGING['max_log_files']:
                try:
                    log_files[0].unlink()
                    log_files = log_files[1:]
                except Exception as e:
                    logging.warning(f"Could not remove old log file")
                    break
        
        logging.info("Texture Extractor initialized")
        
    except Exception as e:
        print("Could not set up logging, using basic console output")
        # Set up basic console logging as fallback
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s'
        )

def check_and_install_dependencies():
    """Check and install required packages."""
    if SKIP_DEPENDENCIES:
        print("\n[i] Skipping dependency checks as SKIP_DEPENDENCIES is True")
        return True
        
    print("\n=== Checking Dependencies ===")
    
    def check_package(package_name):
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False

    def install_package(package_name):
        print(f"  > Installing {package_name}...")
        try:
            # First try with pip
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package_name],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
            
            # Special handling for pywin32
            if package_name == 'pywin32':
                try:
                    # Run post-install script
                    import os
                    python_home = os.path.dirname(sys.executable)
                    scripts_dir = os.path.join(python_home, 'Scripts')
                    post_install_script = os.path.join(scripts_dir, 'pywin32_postinstall.py')
                    if os.path.exists(post_install_script):
                        print("  > Running pywin32 post-install script...")
                        subprocess.check_call([sys.executable, post_install_script, "-install"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                except Exception as e:
                    print(f"  > Warning: pywin32 post-install script failed: {e}")
                    
            return True
        except Exception as pip_error:
            print(f"  > Pip install failed: {pip_error}")
            try:
                # If pip fails, try with easy_install
                subprocess.check_call([sys.executable, "-m", "easy_install", package_name],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                return True
            except Exception as easy_install_error:
                print(f"  > Easy_install failed: {easy_install_error}")
                return False

    missing_packages = []
    installed_packages = []
    critical_packages = ['pywin32', 'vpk']

    # First check what needs to be installed
    print("\nChecking installed packages...")
    for import_name, pip_name in REQUIRED_PACKAGES:
        if pip_name is None:  # Skip built-in packages
            print(f"  [+] {import_name} (built-in)")
            continue
            
        if check_package(import_name):
            print(f"  [+] {import_name} already installed")
            installed_packages.append(import_name)
        else:
            print(f"  [-] {import_name} not found")
            missing_packages.append((import_name, pip_name))

    # If anything needs installing, try to install it
    if missing_packages:
        print("\nAttempting to install missing packages...")
        for import_name, pip_name in missing_packages:
            if install_package(pip_name):
                print(f"  [+] Successfully installed {import_name}")
                installed_packages.append(import_name)
                
                # For pywin32, try to import again after installation
                if pip_name == 'pywin32':
                    try:
                        import win32security
                        print("  [+] Successfully imported win32security after installation")
                    except ImportError as e:
                        print(f"  [!] Failed to import win32security after installation: {e}")
                        return False
            else:
                print(f"  [!] Could not install {import_name}")
                if pip_name in critical_packages:
                    print(f"  [!] {pip_name} is required for core functionality")
                    print(f"  [!] Please install {pip_name} manually using:")
                    print(f"      pip install {pip_name}")
                    return False

    print("\n[+] Dependency check completed")
    return True

def get_available_drives():
    """Get all available drives on Windows."""
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:"
        if os.path.exists(f"{drive}\\"):
            drives.append(drive)
    return drives

def find_steam_path():
    """Find Steam installation path using registry, with fallback paths."""
    print("\n=== Steam Path Detection ===")
    print("Searching for Steam installation...")
    steam_path = None

    # Get all available drives except C:
    drives = [f"{letter}:" for letter in string.ascii_uppercase 
             if letter != 'C' and os.path.exists(f"{letter}:")]
    
    print(f"\nSearching drives: {', '.join(drives)}")
    
    # Search common Steam paths on each drive
    common_subpaths = [
        "SteamLibrary",
        "Steam",
        "Games/Steam",
        "Games/SteamLibrary",
        "Program Files (x86)/Steam",
        "Program Files/Steam"
    ]
    
    for drive in drives:
        print(f"\nChecking drive {drive}")
        for subpath in common_subpaths:
            full_path = Path(f"{drive}/{subpath}")
            print(f"  Checking: {full_path}")
            if full_path.exists():
                print(f"    [+] Path exists")
                if (full_path / "steamapps").exists():
                    steam_path = full_path
                    print(f"    [+] Found valid Steam installation with steamapps folder")
                    return steam_path
                else:
                    print(f"    [-] No steamapps folder found")
            else:
                print(f"    [-] Path does not exist")

    if not steam_path:
        print("\n[-] Error: Could not find Steam installation in any location.")
    
    return steam_path

def find_game_paths(steam_path):
    """Find Source engine games directories, logging all searched paths."""
    if not steam_path:
        print("Error: No Steam path provided")
        return {}

    # Dictionary of game names and their app folders
    source_games = {
        "GarrysMod": "GarrysMod",
        "Half-Life 2": "Half-Life 2",
        "Counter-Strike: Source": "Counter-Strike Source",
        "Team Fortress 2": "Team Fortress 2",
        "Left 4 Dead 2": "Left 4 Dead 2",
        "Portal": "Portal",
        "Half-Life 2: Episode One": "Half-Life 2/episodic",
        "Half-Life 2: Episode Two": "Half-Life 2/ep2",
        "Half-Life: Source": "Half-Life Source",
        "Day of Defeat: Source": "day of defeat source",
        "Counter-Strike: Global Offensive": "Counter-Strike Global Offensive"
    }

    game_paths = {}
    all_library_paths = []
    
    # First, collect ALL possible Steam library locations
    print("\nCollecting Steam library locations...")
    
    # Add main Steam library
    main_library = steam_path / "steamapps"
    if main_library.exists():
        all_library_paths.append(main_library)
        print(f"  [+] Found main Steam library: {main_library}")
    
    # Check libraryfolders.vdf for additional libraries
    library_folders = main_library / "libraryfolders.vdf"
    print(f"  Checking for additional libraries in: {library_folders}")
    if library_folders.exists():
        try:
            with open(library_folders, "r", encoding='utf-8') as f:
                content = f.read()
                
            # Try both old and new format paths
            paths = []
            # New format (path)
            for line in content.split('\n'):
                if '"path"' in line:
                    path = line.split('"')[3].replace("\\\\", "\\")
                    paths.append(path)
            # Old format (direct paths)
            for line in content.split('\n'):
                if '"1"' in line or '"2"' in line or '"3"' in line:
                    if ':\\' in line:  # Only if it contains a path
                        path = line.split('"')[3].replace("\\\\", "\\")
                        paths.append(path)
            
            # Add found paths
            for path in paths:
                library_path = Path(path) / "steamapps"
                if library_path.exists() and library_path not in all_library_paths:
                    all_library_paths.append(library_path)
                    print(f"  [+] Found additional library: {library_path}")
        except Exception as e:
            print(f"  [-] Error reading {library_folders}: {e}")
    
    print(f"\nSearching for Source games in {len(all_library_paths)} Steam libraries...")
    
    # Now search all libraries for games
    for library in all_library_paths:
        common = library / "common"
        print(f"\nChecking library: {common}")
        if common.exists():
            for game_name, folder_name in source_games.items():
                game_path = common / folder_name
                print(f"  Checking for {game_name}: {game_path}")
                if game_path.exists():
                    if game_name not in game_paths:  # Only add if we haven't found it yet
                        game_paths[game_name] = game_path
                        print(f"    [+] Found {game_name}")
                    else:
                        print(f"    [i] Found duplicate {game_name} installation (using first found)")
                else:
                    print(f"    [-] Not found")
        else:
            print(f"  [-] Common directory not found: {common}")

    return game_paths

# VPK patterns and locations
vpk_patterns = [
    "*_dir.vpk",
    "*_000.vpk",
    "*_textures.vpk",
    "*_misc.vpk",
    "*.vpk",
    "*.bsp",
    "*.gma"
]

vpk_locations = {
    "GarrysMod": [
        "garrysmod/hl2",
        "garrysmod/sourceengine",
        "garrysmod",
        "garrysmod/platform",
        "garrysmod/ep2",
        "garrysmod/episodic",
        "garrysmod/css",
        "garrysmod/tf2",
        "garrysmod/l4d2",
        "garrysmod/portal",
        "garrysmod/dod",
        "garrysmod/download",
        "garrysmod/downloads",
        "garrysmod/cache",
        "garrysmod/addons",
        "garrysmod/maps",
        "garrysmod/materials",
        "garrysmod/fastdl",
        "garrysmod/lua",
        "garrysmod/data"
    ],
    "Half-Life 2": ["hl2", "hl2/materials", "hl2/maps"],
    "Counter-Strike: Source": ["cstrike", "cstrike/materials", "cstrike/maps"],
    "Team Fortress 2": ["tf", "tf/materials", "tf/maps"],
    "Left 4 Dead 2": ["left4dead2", "left4dead2/materials", "left4dead2/maps"],
    "Portal": ["portal", "portal/materials", "portal/maps"],
    "Half-Life 2: Episode One": ["episodic", "episodic/materials", "episodic/maps"],
    "Half-Life 2: Episode Two": ["ep2", "ep2/materials", "ep2/maps"],
    "Half-Life: Source": ["hl1", "hl1/materials", "hl1/maps"],
    "Day of Defeat: Source": ["dod", "dod/materials", "dod/maps"],
    "Counter-Strike: Global Offensive": ["csgo", "csgo/materials", "csgo/maps"]
}

def find_vpk_files(game_paths, gui_callback=None, should_continue=None):
    """Find VPK files for Source games, logging all searches."""
    vpk_files = []
    print("\n=== VPK File Detection ===")
    
    def should_stop():
        """Check if we should stop processing."""
        return should_continue and not should_continue()

    def update_gui_found(count):
        """Update GUI with current file count."""
        if gui_callback:
            gui_callback(count)
        return count

    # Get Garry's Mod path
    gmod_path = game_paths.get("GarrysMod")
    if not gmod_path:
        print("Error: Garry's Mod path not found!")
        return vpk_files

    # Process each game's paths
    for game, path in game_paths.items():
        if should_stop():
            return vpk_files
            
        print(f"\nProcessing game: {game}")
        print(f"Base path: {path}")
        
        if game == "GarrysMod":
            # Check workshop content with expanded search
            workshop_paths = [
                path.parent / "workshop" / "content" / "4000",
                path.parent / "workshop" / "content",
                path.parent / "workshop",
                path.parent / "workshop" / "temp",
                path.parent / "workshop" / "downloads"
            ]
            
            for workshop_path in workshop_paths:
                if should_stop():
                    return vpk_files
                    
                if workshop_path.exists():
                    print(f"\nChecking Workshop content: {workshop_path}")
                    for workshop_item in workshop_path.rglob("*"):
                        if should_stop():
                            return vpk_files
                            
                        if workshop_item.is_dir():
                            print(f"  Checking workshop item: {workshop_item.name}")
                            for pattern in vpk_patterns:
                                if should_stop():
                                    return vpk_files
                                    
                                for found_file in workshop_item.rglob(pattern):
                                    if should_stop():
                                        return vpk_files
                                        
                                    if found_file not in vpk_files:
                                        vpk_files.append(found_file)
                                        update_gui_found(len(vpk_files))
                                        print(f"    ✓ Found file: {found_file.name}")
        
        # Check each possible VPK location for this game
        for loc in vpk_locations.get(game, []):
            if should_stop():
                return vpk_files
                
            vpk_dir = path / loc
            print(f"\n  Checking directory: {vpk_dir}")
            
            if vpk_dir.exists():
                for pattern in vpk_patterns:
                    if should_stop():
                        return vpk_files
                        
                    try:
                        for found_file in vpk_dir.rglob(pattern):
                            if should_stop():
                                return vpk_files
                                
                            if found_file not in vpk_files:
                                vpk_files.append(found_file)
                                update_gui_found(len(vpk_files))
                                print(f"    ✓ Found: {found_file.name}")
                    except Exception as e:
                        print(f"    ✗ Error searching pattern {pattern}: {e}")
                
    return vpk_files

def sanitize_path(path):
    """Sanitize file path by removing invalid characters and handling special cases."""
    # Remove any quotes from the path
    path = path.replace('"', '').replace("'", '')
    
    # Remove any parameters that might have been accidentally included
    if '{' in path:
        path = path.split('{')[0].strip()
        
    # Replace invalid Windows filename characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        path = path.replace(char, '_')
        
    # Normalize slashes
    path = path.replace('\\', '/').strip('/')
    
    # Remove any duplicate slashes
    while '//' in path:
        path = path.replace('//', '/')
        
    return path

def create_folder_structure(base_path, file_path):
    """Create folder structure for a given path with robust permission handling."""
    # Sanitize the path first
    file_path = sanitize_path(file_path)
    
    # Remove 'materials/' from the start of the path if it exists
    file_path = file_path.lstrip('/')
    if file_path.lower().startswith('materials/'):
        file_path = file_path[len('materials/'):]
    
    # Convert to Path object for proper path handling
    full_path = Path(base_path) / file_path
    
    try:
        # Create parent directories with explicit permissions
        parent_dir = full_path.parent
        if not parent_dir.exists():
            # First try to create the directory with default permissions
            parent_dir.mkdir(parents=True, exist_ok=True)
            
            # Take ownership and set permissions using multiple methods
            success = False
            
            try:
                # Method 1: Using takeown and icacls with elevated privileges
                subprocess.run(
                    ['takeown', '/F', str(parent_dir), '/R', '/D', 'Y'],
                    capture_output=True, text=True, check=True
                )
                
                subprocess.run(
                    ['icacls', str(parent_dir), '/grant', 'Everyone:(OI)(CI)F', '/T', '/Q', '/C'],
                    capture_output=True, text=True, check=True
                )
                subprocess.run(
                    ['icacls', str(parent_dir), '/grant', 'Administrators:(OI)(CI)F', '/T', '/Q', '/C'],
                    capture_output=True, text=True, check=True
                )
                
                success = True
                logging.debug(f"Successfully set permissions using takeown/icacls for {parent_dir}")
            except Exception as e1:
                logging.debug(f"Method 1 (takeown/icacls) failed: {e1}")
                
                try:
                    # Method 2: Using win32security
                    token = win32security.OpenProcessToken(
                        win32api.GetCurrentProcess(),
                        win32security.TOKEN_QUERY
                    )
                    user = win32security.GetTokenInformation(token, win32security.TokenUser)
                    user_sid = user[0]
                    
                    sd = win32security.SECURITY_DESCRIPTOR()
                    dacl = win32security.ACL()
                    
                    # Add permissions
                    for sid in [user_sid, win32security.ConvertStringSidToSid("S-1-1-0")]:
                        dacl.AddAccessAllowedAce(
                            win32security.ACL_REVISION,
                            win32con.GENERIC_ALL,
                            sid
                        )
                    
                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    win32security.SetFileSecurity(
                        str(parent_dir),
                        win32security.DACL_SECURITY_INFORMATION,
                        sd
                    )
                    
                    success = True
                    logging.debug(f"Successfully set permissions using win32security for {parent_dir}")
                except Exception as e2:
                    logging.debug(f"Method 2 (win32security) failed: {e2}")
                    
                    try:
                        # Method 3: Using cacls as last resort
                        subprocess.run(
                            ['cacls', str(parent_dir), '/E', '/T', '/C', '/G', 'Everyone:F'],
                            capture_output=True, text=True, check=True
                        )
                        success = True
                        logging.debug(f"Successfully set permissions using cacls for {parent_dir}")
                    except Exception as e3:
                        logging.debug(f"Method 3 (cacls) failed: {e3}")
            
            if not success:
                logging.error(f"All permission setting methods failed for {parent_dir}")
                return None
                
    except PermissionError as pe:
        logging.error(f"Permission denied creating directory: {parent_dir}")
        if not check_admin():
            logging.error("Script is not running with administrator privileges")
        return None
    except Exception as e:
        logging.error(f"Error creating directory structure: {e}")
        return None

    return str(full_path)

def open_materials_folder(gmod_path=None):
    """Open the Garry's Mod materials folder in Windows Explorer."""
    try:
        if not gmod_path:
            steam_path = find_steam_path()
            if not steam_path:
                logging.error("Could not find Steam installation")
                return False
            game_paths = find_game_paths(steam_path)
            gmod_path = game_paths.get("GarrysMod")
        
        if not gmod_path:
            logging.error("Could not find Garry's Mod installation")
            return False
        
        materials_path = gmod_path / "garrysmod" / "materials"
        if not materials_path.exists():
            logging.error(f"Materials folder not found at: {materials_path}")
            return False
        
        os.startfile(str(materials_path))
        return True
    except Exception as e:
        logging.error(f"Error opening materials folder: {e}")
        return False

def create_backup(path: Path) -> Optional[str]:
    """Create a backup of the specified path with enhanced options."""
    if not BACKUP['enabled']:
        logging.info("Backup creation is disabled")
        return None

    backup_path = None
    try:
        # Create backup location
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_location = Path(BACKUP['location'] or os.path.expanduser("~/Desktop/texture_backups"))
        backup_path = backup_location / f"backup_{timestamp}"
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_location, exist_ok=True)
        
        # Create backup based on format
        if BACKUP['compression']:
            backup_path = backup_path.with_suffix('.zip')
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in path.rglob('*'):
                    if file.is_file() and should_backup_file(file):
                        try:
                            rel_path = file.relative_to(path)
                            zipf.write(file, rel_path)
                            logging.debug(f"Backed up: {rel_path}")
                        except Exception as e:
                            logging.warning(f"Failed to backup file {file}: {e}")
        else:
            backup_dir = backup_path.with_suffix('')
            for file in path.rglob('*'):
                if file.is_file() and should_backup_file(file):
                    try:
                        rel_path = file.relative_to(path)
                        target = backup_dir / rel_path
                        os.makedirs(target.parent, exist_ok=True)
                        shutil.copy2(file, target)
                        logging.debug(f"Backed up: {rel_path}")
                    except Exception as e:
                        logging.warning(f"Failed to backup file {file}: {e}")
        
        logging.info(f"Created backup at: {backup_path}")
        return str(backup_path)
        
    except Exception as e:
        logging.error(f"Failed to create backup: {e}")
        if backup_path and backup_path.exists():
            try:
                backup_path.unlink()
            except Exception as cleanup_error:
                logging.warning(f"Failed to clean up failed backup: {cleanup_error}")
        return None

def _verify_backup(backup_path: Path, manifest: dict) -> bool:
    """Verify backup integrity."""
    try:
        if BACKUP['compression']:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Check file list matches manifest
                zip_files = set(zipf.namelist())
                manifest_files = set(manifest['files'])
                if zip_files != manifest_files:
                    logging.error("Backup file list mismatch")
                    return False
                return True
        else:
            # Verify directory backup
            backup_dir = backup_path.with_suffix('')
            for file_path in manifest['files']:
                if not (backup_dir / file_path).exists():
                    logging.error(f"Missing file in backup: {file_path}")
                    return False
            return True
    except Exception as e:
        logging.error(f"Backup verification failed: {e}")
        return False

def create_vmt_file(vmt_path, content):
    """Create a VMT file with robust permission handling."""
    try:
        # Create the directory structure first
        vmt_dir = os.path.dirname(vmt_path)
        if not os.path.exists(vmt_dir):
            result = create_folder_structure(vmt_dir, "")
            if result is None:
                return False

        # Try to write the file with proper permissions
        success = False
        
        # Method 1: Direct file write with basic permissions
        try:
            with open(vmt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            success = True
        except Exception as e:
            logging.debug(f"Basic file write failed: {e}")
            
            # Method 2: Using icacls
            try:
                # First set directory permissions
                subprocess.run(
                    ['icacls', vmt_dir, '/grant', 'Everyone:(OI)(CI)F', '/T', '/Q'],
                    capture_output=True, text=True, check=True
                )
                
                # Then try writing file again
                with open(vmt_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                success = True
            except Exception as e2:
                logging.debug(f"ICACLS method failed: {e2}")
                
                # Method 3: Using win32security as last resort
                try:
                    token = win32security.OpenProcessToken(
                        win32api.GetCurrentProcess(),
                        win32security.TOKEN_QUERY
                    )
                    user = win32security.GetTokenInformation(token, win32security.TokenUser)
                    
                    sd = win32security.SECURITY_DESCRIPTOR()
                    dacl = win32security.ACL()
                    
                    dacl.AddAccessAllowedAce(
                        win32security.ACL_REVISION,
                        win32con.GENERIC_ALL,
                        user[0]
                    )
                    
                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    
                    # Set directory permissions
                    win32security.SetFileSecurity(
                        vmt_dir,
                        win32security.DACL_SECURITY_INFORMATION,
                        sd
                    )
                    
                    # Try writing file one last time
                    with open(vmt_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    success = True
                except Exception as e3:
                    logging.debug(f"Win32security method failed: {e3}")
        
        if not success:
            logging.error(f"Failed to create VMT file after all attempts: {vmt_path}")
            return False
            
        return True
        
    except Exception as e:
        logging.error(f"Error creating VMT file: {e}")
        return False

def should_backup_file(file_path: Path) -> bool:
    """Determine if a file should be included in backup based on settings."""
    if not BACKUP['enabled']:
        return False
        
    # Check file extension
    ext = file_path.suffix.lower()
    
    # Always backup VMT and VTF files
    if ext in ['.vmt', '.vtf']:
        return True
        
    # Backup config files if enabled
    if BACKUP['include_cfg'] and ext == '.cfg':
        return True
        
    # Backup material files if enabled
    if BACKUP['include_materials'] and 'materials' in str(file_path):
        return True
        
    return False

class SettingsDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog on parent
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 600) // 2
        self.dialog.geometry(f"500x600+{x}+{y}")
        
        # Create main container with scrollbar
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create frame for settings
        self.settings_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.settings_frame, anchor="nw")
        
        # Add settings sections
        self._add_texture_settings()
        self._add_backup_settings()
        self._add_transparency_settings()
        self._add_performance_settings()
        self._add_logging_settings()
        
        # Add save button at bottom
        save_button = ttk.Button(self.dialog, text="Save Settings", command=self._save_settings)
        save_button.pack(pady=20)
        
        # Update scroll region
        self.settings_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Add mousewheel scrolling
        self.dialog.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
        
    def _add_section(self, title):
        """Add a new settings section with a title"""
        frame = ttk.LabelFrame(self.settings_frame, text=title, padding="10")
        frame.pack(fill=tk.X, padx=5, pady=5)
        return frame
        
    def _add_texture_settings(self):
        frame = self._add_section("Texture Processing")
        
        # Texture quality settings
        self.texture_vars = {
            'compress_textures': tk.BooleanVar(value=TEXTURE_QUALITY['compress_textures']),
            'max_texture_size': tk.StringVar(value=str(TEXTURE_QUALITY['max_texture_size'])),
            'mipmap_generation': tk.BooleanVar(value=TEXTURE_QUALITY['mipmap_generation'])
        }
        
        ttk.Checkbutton(frame, text="Compress Textures", variable=self.texture_vars['compress_textures']).pack(anchor="w")
        
        size_frame = ttk.Frame(frame)
        size_frame.pack(fill=tk.X, pady=5)
        ttk.Label(size_frame, text="Max Texture Size:").pack(side=tk.LEFT)
        ttk.Entry(size_frame, textvariable=self.texture_vars['max_texture_size'], width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(frame, text="Generate Mipmaps", variable=self.texture_vars['mipmap_generation']).pack(anchor="w")
        
    def _add_backup_settings(self):
        frame = self._add_section("Backup Settings")
        
        self.backup_vars = {
            'enabled': tk.BooleanVar(value=BACKUP['enabled']),
            'compression': tk.BooleanVar(value=BACKUP['compression']),
            'max_backups': tk.StringVar(value=str(BACKUP['max_backups'])),
            'include_cfg': tk.BooleanVar(value=BACKUP['include_cfg']),
            'include_materials': tk.BooleanVar(value=BACKUP['include_materials'])
        }
        
        ttk.Checkbutton(frame, text="Enable Backups", variable=self.backup_vars['enabled']).pack(anchor="w")
        ttk.Checkbutton(frame, text="Use Compression", variable=self.backup_vars['compression']).pack(anchor="w")
        
        max_frame = ttk.Frame(frame)
        max_frame.pack(fill=tk.X, pady=5)
        ttk.Label(max_frame, text="Max Backups:").pack(side=tk.LEFT)
        ttk.Entry(max_frame, textvariable=self.backup_vars['max_backups'], width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(frame, text="Include Config Files", variable=self.backup_vars['include_cfg']).pack(anchor="w")
        ttk.Checkbutton(frame, text="Include Material Files", variable=self.backup_vars['include_materials']).pack(anchor="w")
        
    def _add_transparency_settings(self):
        frame = self._add_section("Transparency Settings")
        
        self.transparency_vars = {
            'default_alpha': tk.StringVar(value=str(TRANSPARENCY['default_alpha'])),
            'weapon_alpha': tk.StringVar(value=str(TRANSPARENCY['weapon_alpha'])),
            'effect_alpha': tk.StringVar(value=str(TRANSPARENCY['effect_alpha'])),
            'enable_fade': tk.BooleanVar(value=TRANSPARENCY['enable_fade'])
        }
        
        # Create labeled entries for alpha values
        for label, key in [
            ("Default Alpha:", 'default_alpha'),
            ("Weapon Alpha:", 'weapon_alpha'),
            ("Effect Alpha:", 'effect_alpha')
        ]:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=self.transparency_vars[key], width=10).pack(side=tk.LEFT, padx=5)
            
        ttk.Checkbutton(frame, text="Enable Distance Fade", variable=self.transparency_vars['enable_fade']).pack(anchor="w")
        
    def _add_performance_settings(self):
        frame = self._add_section("Performance Settings")
        
        self.performance_vars = {
            'cache_enabled': tk.BooleanVar(value=PERFORMANCE['cache_enabled']),
            'cache_size': tk.StringVar(value=str(PERFORMANCE['cache_size'])),
            'preload_textures': tk.BooleanVar(value=PERFORMANCE['preload_textures']),
            'batch_processing': tk.BooleanVar(value=PERFORMANCE['batch_processing']),
            'batch_size': tk.StringVar(value=str(PERFORMANCE['batch_size']))
        }
        
        ttk.Checkbutton(frame, text="Enable Cache", variable=self.performance_vars['cache_enabled']).pack(anchor="w")
        
        cache_frame = ttk.Frame(frame)
        cache_frame.pack(fill=tk.X, pady=5)
        ttk.Label(cache_frame, text="Cache Size (MB):").pack(side=tk.LEFT)
        ttk.Entry(cache_frame, textvariable=self.performance_vars['cache_size'], width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(frame, text="Preload Textures", variable=self.performance_vars['preload_textures']).pack(anchor="w")
        ttk.Checkbutton(frame, text="Batch Processing", variable=self.performance_vars['batch_processing']).pack(anchor="w")
        
        batch_frame = ttk.Frame(frame)
        batch_frame.pack(fill=tk.X, pady=5)
        ttk.Label(batch_frame, text="Batch Size:").pack(side=tk.LEFT)
        ttk.Entry(batch_frame, textvariable=self.performance_vars['batch_size'], width=10).pack(side=tk.LEFT, padx=5)
        
    def _add_logging_settings(self):
        frame = self._add_section("Logging Settings")
        
        self.logging_vars = {
            'log_to_file': tk.BooleanVar(value=LOGGING['log_to_file']),
            'max_log_size': tk.StringVar(value=str(LOGGING['max_log_size'])),
            'max_log_files': tk.StringVar(value=str(LOGGING['max_log_files']))
        }
        
        ttk.Checkbutton(frame, text="Log to File", variable=self.logging_vars['log_to_file']).pack(anchor="w")
        
        size_frame = ttk.Frame(frame)
        size_frame.pack(fill=tk.X, pady=5)
        ttk.Label(size_frame, text="Max Log Size (MB):").pack(side=tk.LEFT)
        ttk.Entry(size_frame, textvariable=self.logging_vars['max_log_size'], width=10).pack(side=tk.LEFT, padx=5)
        
        files_frame = ttk.Frame(frame)
        files_frame.pack(fill=tk.X, pady=5)
        ttk.Label(files_frame, text="Max Log Files:").pack(side=tk.LEFT)
        ttk.Entry(files_frame, textvariable=self.logging_vars['max_log_files'], width=10).pack(side=tk.LEFT, padx=5)
        
    def _save_settings(self):
        """Save all settings to global configuration"""
        try:
            # Update texture settings
            TEXTURE_QUALITY.update({
                'compress_textures': self.texture_vars['compress_textures'].get(),
                'max_texture_size': int(self.texture_vars['max_texture_size'].get()),
                'mipmap_generation': self.texture_vars['mipmap_generation'].get()
            })
            
            # Update backup settings
            BACKUP.update({
                'enabled': self.backup_vars['enabled'].get(),
                'compression': self.backup_vars['compression'].get(),
                'max_backups': int(self.backup_vars['max_backups'].get()),
                'include_cfg': self.backup_vars['include_cfg'].get(),
                'include_materials': self.backup_vars['include_materials'].get()
            })
            
            # Update transparency settings
            TRANSPARENCY.update({
                'default_alpha': float(self.transparency_vars['default_alpha'].get()),
                'weapon_alpha': float(self.transparency_vars['weapon_alpha'].get()),
                'effect_alpha': float(self.transparency_vars['effect_alpha'].get()),
                'enable_fade': self.transparency_vars['enable_fade'].get()
            })
            
            # Update performance settings
            PERFORMANCE.update({
                'cache_enabled': self.performance_vars['cache_enabled'].get(),
                'cache_size': int(self.performance_vars['cache_size'].get()),
                'preload_textures': self.performance_vars['preload_textures'].get(),
                'batch_processing': self.performance_vars['batch_processing'].get(),
                'batch_size': int(self.performance_vars['batch_size'].get())
            })
            
            # Update logging settings
            LOGGING.update({
                'log_to_file': self.logging_vars['log_to_file'].get(),
                'max_log_size': int(self.logging_vars['max_log_size'].get()),
                'max_log_files': int(self.logging_vars['max_log_files'].get())
            })
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", "Please enter valid numeric values for all number fields.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

class TextureExtractorGUI:
    def __init__(self):
        logging.info("Initializing GUI...")
        
        # Initialize the main window
        self.window = tk.Tk()
        self.window.title(f"Texture Extractor v{VERSION}")
        self.window.geometry("400x500")
        self.window.resizable(False, False)
        logging.info("Main window created")
        
        # Center the window on screen
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 500) // 2
        self.window.geometry(f"400x500+{x}+{y}")
        logging.info("Window positioned")

        # Configure main window grid
        self.window.grid_columnconfigure(0, weight=1)
        
        # Initialize state variables
        self.is_processing = False
        self.processing_thread = None
        self.files_found = 0
        self.processed_files = 0
        self.total_files = 0
        self.start_time = None
        self.last_gui_update = 0
        self.gui_update_interval = 100
        self.progress_var = tk.DoubleVar()
        self.errors = 0
        logging.info("State variables initialized")
        
        # Add cache variables
        self.steam_path = None
        self.game_paths = None
        self.vpk_files = None
        self.preload_complete = False
        self.preload_thread = None
        
        try:
            # Create main container
            self.main_container = ttk.Frame(self.window, padding="20")
            self.main_container.grid(row=0, column=0, sticky="nsew")
            self.main_container.grid_columnconfigure(0, weight=1)
            logging.info("Main container created")
            
            # Setup GUI components
            self._setup_gui()
            logging.info("GUI components set up")
            
            # Make sure window appears on top
            self.window.lift()
            self.window.attributes('-topmost', True)
            self.window.after(1000, lambda: self.window.attributes('-topmost', False))
            
            # Force an update to show the window
            self.window.update()
            logging.info("Window visibility enforced")
            
            # Start preloading
            self.start_preload()
            logging.info("Preload started")
            
            # Start GUI update loop
            self._update_gui()
            logging.info("GUI update loop started")
            
        except Exception as e:
            logging.error(f"Error during GUI initialization: {e}")
            raise

    def run(self):
        """Start the GUI main loop"""
        try:
            logging.info("Entering main loop")
            self.window.mainloop()
            logging.info("Main loop ended")
        except Exception as e:
            logging.error(f"GUI error in main loop: {e}")
            raise
        finally:
            logging.info("Cleaning up GUI resources")
            self.is_processing = False
            if self.processing_thread and self.processing_thread.is_alive():
                try:
                    self.processing_thread.join(timeout=1.0)
                except Exception as e:
                    logging.error(f"Error stopping thread during shutdown: {e}")

    def start_preload(self):
        """Start preloading data in a separate thread."""
        self.status_label.config(text="Preloading data...")
        self.start_button.config(state="disabled")
        self.preload_thread = threading.Thread(target=self._preload_data)
        self.preload_thread.daemon = True
        self.preload_thread.start()

    def _setup_gui(self):
        """Setup GUI components"""
        try:
            # Title with proper styling
            self.title_label = ttk.Label(
                self.main_container, 
                text=f"Texture Extractor v{VERSION}", 
                font=('Helvetica', 16, 'bold'),
                anchor="center"
            )
            self.title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

            # Button frame for better organization
            button_frame = ttk.Frame(self.main_container)
            button_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="ew")
            button_frame.grid_columnconfigure(0, weight=1)
            button_frame.grid_columnconfigure(1, weight=1)
            button_frame.grid_columnconfigure(2, weight=1)  # Add column for settings button

            # Buttons with consistent width
            button_width = 15
            self.start_button = ttk.Button(
                button_frame, 
                text="Start Processing", 
                command=self.start_processing,
                width=button_width
            )
            self.start_button.grid(row=0, column=0, padx=5)

            self.stop_button = ttk.Button(
                button_frame, 
                text="Stop", 
                command=self.stop_processing,
                width=button_width,
                state=tk.DISABLED
            )
            self.stop_button.grid(row=0, column=1, padx=5)

            # Add settings button
            self.settings_button = ttk.Button(
                button_frame,
                text="Settings",
                command=self.show_settings,
                width=button_width
            )
            self.settings_button.grid(row=0, column=2, padx=5)

            # Status label with proper wrapping
            self.status_label = ttk.Label(
                self.main_container, 
                text="Ready to process...",
                wraplength=350,
                justify="center"
            )
            self.status_label.grid(row=2, column=0, columnspan=2, pady=(10, 10), sticky="ew")

            # Progress bar with fixed width
            self.progress_bar = ttk.Progressbar(
                self.main_container, 
                length=350, 
                mode='determinate'
            )
            self.progress_bar.grid(row=3, column=0, columnspan=2, pady=(0, 20), sticky="ew")

            # Stats frame with proper styling
            self.stats_frame = ttk.LabelFrame(
                self.main_container, 
                text="Statistics", 
                padding="10"
            )
            self.stats_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5)

            # Configure stats frame grid
            self.stats_frame.grid_columnconfigure(0, weight=1)
            self.stats_frame.grid_columnconfigure(1, weight=1)

            # Stats labels with consistent formatting
            self.stats_labels = {}
            stats_to_show = [
                ('Files Found:', 'found', '0'),
                ('Files Processed:', 'files', '0'),
                ('Success Rate:', 'rate', '0%'),
                ('Errors:', 'errors', '0'),
                ('Processing Time:', 'time', '0:00:00')
            ]
            
            for i, (label_text, key, initial_value) in enumerate(stats_to_show):
                container = ttk.Frame(self.stats_frame)
                container.grid(row=i, column=0, columnspan=2, sticky="ew", pady=2)
                container.grid_columnconfigure(1, weight=1)
                
                label = ttk.Label(container, text=label_text)
                label.grid(row=0, column=0, sticky="w", padx=(0, 10))
                
                value_label = ttk.Label(container, text=initial_value)
                value_label.grid(row=0, column=1, sticky="e")
                self.stats_labels[key] = value_label

            # Summary labels at the bottom
            self.files_found_label = ttk.Label(
                self.stats_frame, 
                text="Files Found: 0",
                anchor="w"
            )
            self.files_found_label.grid(row=len(stats_to_show), column=0, columnspan=2, pady=(10, 0), sticky="ew")

            self.processed_label = ttk.Label(
                self.stats_frame, 
                text="Processed: 0/0",
                anchor="w"
            )
            self.processed_label.grid(row=len(stats_to_show) + 1, column=0, columnspan=2, pady=(0, 10), sticky="ew")

            logging.info("GUI components initialized successfully")
            
        except Exception as e:
            logging.error(f"Error setting up GUI components: {e}")
            raise

    def _update_stats(self):
        """Update statistics display"""
        try:
            # Update file counts
            self.stats_labels['found'].config(text=str(self.files_found))
            self.stats_labels['files'].config(text=str(self.processed_files))
            
            # Update success rate
            if self.processed_files > 0:
                success_rate = ((self.processed_files - self.errors) / self.processed_files) * 100
                self.stats_labels['rate'].config(text=f"{success_rate:.1f}%")
            else:
                self.stats_labels['rate'].config(text="0%")
            
            # Update processing time
            if self.start_time:
                elapsed = time.time() - self.start_time
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                self.stats_labels['time'].config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                self.stats_labels['time'].config(text="00:00:00")
            
            # Update error count
            self.stats_labels['errors'].config(text=str(self.errors))
            
            # Update summary labels
            self.files_found_label.config(text=f"Files Found: {self.files_found}")
            self.processed_label.config(text=f"Processed: {self.processed_files}/{self.total_files}")
            
        except Exception as e:
            logging.error(f"Error updating stats: {e}")
            # Don't re-raise the exception to prevent GUI crashes

    def _update_gui(self):
        """Update GUI elements periodically"""
        current_time = time.time() * 1000
        if current_time - self.last_gui_update >= self.gui_update_interval:
            if self.is_processing and self.start_time:
                elapsed_time = time.time() - self.start_time
                self.status_label.config(text=f"Processing... Time: {elapsed_time:.1f}s")
                
                if self.total_files > 0:
                    progress = (self.processed_files / self.total_files) * 100
                    self.progress_bar["value"] = progress
                    
                self.files_found_label.config(text=f"Files Found: {self.files_found}")
                self.processed_label.config(text=f"Processed: {self.processed_files}/{self.total_files}")
            
            self.window.update_idletasks()
            self.last_gui_update = current_time
            
        self.window.after(10, self._update_gui)  # Schedule next update

    def _process_task(self):
        """Process files using preloaded data."""
        try:
            if not self.preload_complete:
                self.status_label.config(text="Error: Preload not complete!")
                return

            self.start_time = time.time()
            self.errors = 0
            
            # Get Garry's Mod path for VMT creation
            gmod_path = self.game_paths.get("GarrysMod")
            if not gmod_path:
                self.status_label.config(text="Error: Garry's Mod path not found!")
                return
                
            gmod_materials = gmod_path / "garrysmod" / "materials"
            all_texture_paths = []
            
            # Process VPK files in chunks
            chunk_size = 5
            vpk_chunks = [self.vpk_files[i:i + chunk_size] for i in range(0, len(self.vpk_files), chunk_size)]
            
            # Process each chunk
            for vpk_chunk in vpk_chunks:
                if not self.is_processing:
                    break
                    
                for path in vpk_chunk:
                    if not self.is_processing:
                        break
                        
                    try:
                        textures = process_file(path)
                        if textures:
                            all_texture_paths.extend(textures)
                        self.processed_files += 1
                        
                        if self.total_files > 0:
                            progress = (self.processed_files / self.total_files) * 50
                            self.progress_bar["value"] = progress
                            self._update_stats()
                            self.window.update_idletasks()
                    except Exception as e:
                        logging.error(f"Error processing {path}: {str(e)}")
                        self.errors += 1
                
                time.sleep(0.01)
            
            # Create VMT files if we have textures
            if all_texture_paths and self.is_processing:
                self.status_label.config(text=f"Creating VMT files for {len(all_texture_paths)} textures...")
                self.window.update_idletasks()
                
                vmt_count = 0
                total_textures = len(all_texture_paths)
                
                for vtf_path in sorted(all_texture_paths):
                    if not self.is_processing:
                        break
                        
                    try:
                        vmt_path = vtf_path.replace('.vtf', '.vmt')
                        full_path = create_folder_structure(gmod_materials, vmt_path)
                        
                        if full_path:
                            vmt_content, vmt_type = create_vmt_content(vtf_path)
                            if vmt_content:
                                parent_dir = os.path.dirname(full_path)
                                if not os.path.exists(parent_dir):
                                    os.makedirs(parent_dir, exist_ok=True)
                                
                                with open(full_path, 'w', encoding='utf-8') as f:
                                    f.write(vmt_content)
                                
                                vmt_count += 1
                                progress = 50 + (vmt_count / total_textures) * 50
                                self.progress_bar["value"] = progress
                                
                                if vmt_count % 10 == 0:
                                    self.status_label.config(text=f"Created {vmt_count} of {total_textures} VMT files...")
                                    self._update_stats()
                                    self.window.update_idletasks()
                    except Exception as e:
                        logging.error(f"Error creating VMT for {vtf_path}: {e}")
                        self.errors += 1
                
                if self.is_processing:
                    self.status_label.config(text=f"Processing completed! Created {vmt_count} VMT files.")
                else:
                    self.status_label.config(text="Processing stopped.")
            else:
                if self.is_processing:
                    self.status_label.config(text="No textures found to process.")
                else:
                    self.status_label.config(text="Processing stopped.")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            logging.error(f"Processing error: {str(e)}")
            self.errors += 1
        finally:
            self.is_processing = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self._update_stats()
            self.window.update_idletasks()

    def start_processing(self):
        """Start the processing task using preloaded data."""
        if not self.is_processing:
            if not self.preload_complete:
                self.status_label.config(text="Please wait for preload to complete...")
                return
            
            # Reset stats only when starting a new process
            self._reset_stats()
            
            self.is_processing = True
            self.start_time = time.time()
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.status_label.config(text="Starting processing...")
            
            self.processing_thread = threading.Thread(target=self._process_task)
            self.processing_thread.daemon = True
            self.processing_thread.start()

    def stop_processing(self):
        """Stop the processing task."""
        if self.is_processing:
            self.is_processing = False
            self.status_label.config(text="Stopping...")
            self.stop_button.config(state="disabled")
            self.window.update_idletasks()
            
            try:
                if self.processing_thread:
                    self.processing_thread.join(timeout=1.0)
            except Exception as e:
                logging.error(f"Error stopping thread: {str(e)}")
            
            # Reset stats only when explicitly stopping
            self._reset_stats()
            self.start_button.config(state="normal")
            self.status_label.config(text="Stopped")
            self.window.update_idletasks()

    def _reset_stats(self):
        """Reset all statistics counters and update GUI."""
        if not self.preload_complete:
            # Don't reset file counts during preload
            self.processed_files = 0
            self.start_time = None
            self.errors = 0
        else:
            # Keep preloaded file counts
            self.processed_files = 0
            self.start_time = None
            self.errors = 0
            self.files_found = self.total_files  # Keep preloaded count
        
        # Reset progress bar
        self.progress_bar["value"] = 0
        
        # Update all stat labels
        self._update_stats()
        
        # Update GUI
        self.window.update_idletasks()

    def update_files_found(self, count):
        """Update the count of files found"""
        self.files_found = count
        self.total_files = count
        self.window.update_idletasks()

    def _preload_data(self):
        """Preload Steam paths, game paths, and VPK files."""
        try:
            # Find Steam installation
            self.status_label.config(text="Looking for Steam installation...")
            self.window.update_idletasks()
            self.steam_path = find_steam_path()
            
            if not self.steam_path:
                self.status_label.config(text="Error: Steam installation not found!")
                self.start_button.config(state="normal")
                return

            # Find game paths
            self.status_label.config(text="Detecting installed games...")
            self.window.update_idletasks()
            self.game_paths = find_game_paths(self.steam_path)
            
            if not self.game_paths:
                self.status_label.config(text="Error: No supported games found!")
                self.start_button.config(state="normal")
                return

            # Find VPK files
            self.status_label.config(text="Scanning for content files...")
            self.window.update_idletasks()
            self.vpk_files = find_vpk_files(
                self.game_paths,
                self.update_files_found,
                lambda: True  # Always continue during preload
            )
            
            if not self.vpk_files:
                self.status_label.config(text="No content files found!")
                self.start_button.config(state="normal")
                return
            
            self.total_files = len(self.vpk_files)
            self.preload_complete = True
            self.status_label.config(text=f"Ready to process {self.total_files} files")
            self.start_button.config(state="normal")
            
            # Update stats display
            self.files_found = self.total_files
            self._update_stats()
            
        except Exception as e:
            logging.error(f"Error during preload: {e}")
            self.status_label.config(text=f"Error during preload: {str(e)}")
            self.start_button.config(state="normal")

    def show_settings(self):
        """Show the settings dialog"""
        try:
            SettingsDialog(self.window)
        except Exception as e:
            logging.error(f"Error showing settings dialog: {e}")
            messagebox.showerror("Error", f"Failed to open settings: {str(e)}")

def main():
    try:
        # Initialize logging first
        setup_logging()
        logging.info("Starting application...")
        
        # Check for admin rights at startup
        if not check_admin():
            logging.warning("Script is not running with administrator privileges")
            print("\nAdministrator privileges are required to modify Garry's Mod files.")
            print("Please run this script as administrator.")
            
            if request_admin():
                logging.info("Restarting script with administrator privileges...")
                print("\nRestarting with administrator privileges...")
                print("Please wait...")
                time.sleep(2)
                elevate_script()
                sys.exit(0)
            else:
                logging.warning("User declined to run as administrator")
                print("\nScript cannot continue without administrator privileges.")
                sys.exit(1)

        # Pre-check Garry's Mod materials directory permissions
        steam_path = find_steam_path()
        if steam_path:
            game_paths = find_game_paths(steam_path)
            gmod_path = game_paths.get("GarrysMod")
            if gmod_path:
                materials_path = Path(gmod_path) / "garrysmod" / "materials"
                try:
                    test_dir = materials_path / "_test_permissions"
                    if not test_dir.exists():
                        test_dir.mkdir(parents=True, exist_ok=True)
                        test_file = test_dir / "test.txt"
                        test_file.write_text("test")
                        test_file.unlink()
                        test_dir.rmdir()
                    logging.info("Successfully verified materials directory permissions")
                except Exception as e:
                    logging.error(f"Failed to verify materials directory permissions: {e}")
                    print("\nError: Cannot write to Garry's Mod materials directory.")
                    print("Please ensure you have full permissions to the Garry's Mod folder.")
                    sys.exit(1)

        # Check if Windows modules are available
        if not HAS_WIN32:
            logging.error("Windows modules not available. Please install pywin32.")
            sys.exit(1)
        
        # Initialize GUI if enabled
        if GUI['enable_gui'] and HAS_GUI:
            logging.info("Starting in GUI mode")
            try:
                # First check if tkinter is working
                test_window = tk.Tk()
                test_window.withdraw()
                test_window.update()
                test_window.destroy()
                logging.info("Tkinter test successful")
                
                # Now create the actual GUI
                logging.info("Creating GUI instance")
                gui = TextureExtractorGUI()
                logging.info("Starting GUI main loop")
                gui.run()
                logging.info("GUI closed normally")
            except Exception as e:
                logging.error(f"Failed to create GUI: {e}")
                print(f"\nError creating GUI: {e}")
                print("Falling back to console mode...")
                # TODO: Implement console mode
        else:
            logging.info("Starting in console mode")
            # TODO: Implement console mode processing

    except KeyboardInterrupt:
        logging.info("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()