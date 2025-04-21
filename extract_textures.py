"""
Extract Textures - Garry's Mod Texture Modification Tool
Version: 1.0.0

=== README ===
This tool is designed to modify textures in Garry's Mod, providing features like:
- Weapon colorization based on weapon types
- Transparency effects for non-weapon objects
- Custom sound modifications
- Automatic backup creation
- Support for VPK, BSP, and GMA files
- Workshop content processing

Features:
- Automatic detection of Steam and game installations
- Intelligent weapon categorization and coloring
- Configurable transparency for non-weapon items
- Backup creation before modifications
- Custom sound script integration
- Extensive logging and progress tracking

Requirements:
- Python 3.6 or higher
- Required packages (auto-installed if SKIP_DEPENDENCIES = False):
  - vpk: For VPK file handling
  - pathlib: For path handling
  - Other standard library packages

Usage:
1. Run the script
2. Wait for it to detect your Steam installation and games
3. Let it process all found content
4. Restart Garry's Mod to see the changes

Configuration:
Edit the configuration section to customize:
- SKIP_DEPENDENCIES: Auto-install required packages
- ENABLE_WEAPON_COLORS: Colorize weapons
- ENABLE_TRANSPARENCY: Make objects transparent
- ENABLE_CUSTOM_SOUNDS: Add custom sound effects
- Weapon categories and colors
- Transparency levels

=== CHANGELOG ===
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

import sys
import subprocess
import os
import winreg
import string
import struct
import mmap
from pathlib import Path

# =============================================================================
# ===== CONFIGURATION OPTIONS =====
# =============================================================================

# -----------------------------------------------------------------------------
# Basic Options
# -----------------------------------------------------------------------------

# Enable/disable features
SKIP_DEPENDENCIES = False    # Set to False to enable automatic dependency installation
ENABLE_WEAPON_COLORS = True  # Set to False to disable all weapon coloring
ENABLE_TRANSPARENCY = True   # Set to False to disable transparency for non-weapon items
ENABLE_CUSTOM_SOUNDS = True  # Set to False to disable custom sound creation

# -----------------------------------------------------------------------------
# Transparency Settings
# -----------------------------------------------------------------------------

# Alpha value for transparent items (0.0 to 1.0)
# Lower values = more transparent
TRANSPARENCY_ALPHA = 0.85

# -----------------------------------------------------------------------------
# Default Weapon Settings
# -----------------------------------------------------------------------------

# Default color for unrecognized weapons
DEFAULT_WEAPON_COLOR = '[1 1 0]'  # Yellow
DEFAULT_WEAPON_COLOR_NAME = 'Yellow'

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

# List of required packages with their pip install names
REQUIRED_PACKAGES = [
    ('vpk', 'vpk'),  # For VPK file handling
    ('shutil', None),         # Built-in, for file operations
    ('pathlib', 'pathlib'),   # For path handling
    ('struct', None),         # Built-in, for binary data
    ('mmap', None),           # Built-in, for memory mapping
    ('winreg', None)          # Built-in, for registry access
]

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
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
            return True
        except:
            try:
                # If pip fails, try with easy_install
                subprocess.check_call([sys.executable, "-m", "easy_install", package_name],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                return True
            except:
                print(f"  > Failed to install {package_name}, skipping...")
                return False

    def ensure_pip():
        """Ensure pip is installed and up to date."""
        try:
            # Try importing pip
            import pip
            print("  [+] Pip is installed")
            
            # Try to upgrade pip
            try:
                print("  > Upgrading pip...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                print("  [+] Pip is up to date")
            except:
                print("  > Failed to upgrade pip, continuing anyway...")
            return True
        except ImportError:
            print("  [!] Pip not found, attempting to install...")
            try:
                # Try to install pip using ensurepip
                subprocess.check_call([sys.executable, "-m", "ensurepip", "--default-pip"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                print("  [+] Successfully installed pip")
                return True
            except:
                print("  > Failed to install pip, will try to continue without it...")
                return False

    # First try to ensure pip is installed, but continue even if it fails
    ensure_pip()

    missing_packages = []
    installed_packages = []

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
            else:
                print(f"  [!] Could not install {import_name}, some features may not work")

    print("\n[+] Dependency check completed")
    if len(installed_packages) < len(REQUIRED_PACKAGES) - sum(1 for _, pip in REQUIRED_PACKAGES if pip is None):
        print("  [!] Warning: Some dependencies could not be installed")
        print("      The script will continue but some features may not work")
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

def find_vpk_files(game_paths):
    """Find VPK files for Source games, logging all searches."""
    vpk_files = []
    print("\n=== VPK File Detection ===")
    
    # Initialize statistics tracking
    global stats
    stats = {
        'vpk_count': 0,
        'bsp_count': 0,
        'vpk_textures': 0,
        'bsp_textures': 0,
        'workshop_items': 0,
        'custom_maps': 0
    }
    
    # Get Garry's Mod path
    gmod_path = game_paths.get("GarrysMod")
    if not gmod_path:
        print("Error: Garry's Mod path not found!")
        return vpk_files

    # Workshop and cache paths relative to Garry's Mod installation
    gmod_relative_paths = [
        # Core workshop and cache paths
        "garrysmod/cache/workshop",
        "garrysmod/cache/workshop/*",
        "garrysmod/download/workshop",
        "garrysmod/downloads/workshop",
        "garrysmod/cache",
        "garrysmod/addons/workshop",
        "garrysmod/workshop_cache",
        
        # Parent steamapps workshop paths
        "../workshop/content/4000",
        "../workshop/downloads",
        "../workshop/temp",
        "../workshop/content",
        "../workshop/cache",
        
        # Additional cache locations
        "garrysmod/cache/temp",
        "garrysmod/cache/http",
        "garrysmod/cache/lua",
        "garrysmod/cache/materials",
        "garrysmod/cache/maps",
        "garrysmod/cache/game",
        "garrysmod/cache/downloads",
        "garrysmod/cache/workshop_cache",
        
        # Workshop content paths
        "garrysmod/workshop",
        "garrysmod/workshop/*",
        "garrysmod/workshop/maps",
        "garrysmod/workshop/temp",
        "garrysmod/workshop/extracted",
        "garrysmod/workshop/ugc",
        
        # Additional download paths
        "garrysmod/downloads/server",
        "garrysmod/downloads/cache",
        "garrysmod/download/cache",
        "garrysmod/download/temp",
        
        # Backup and temp paths
        "garrysmod/_workshop",
        "garrysmod/_cache",
        "garrysmod/_downloads",
        "garrysmod/workshop_temp",
        
        # Legacy paths
        "garrysmod/download/workshop_cache",
        "garrysmod/downloads/workshop_cache",
        "garrysmod/cache/workshop_temp",
        "garrysmod/workshop_downloads"
    ]
    
    # Get Steam path and add additional workshop locations
    steam_path = gmod_path.parent.parent  # steamapps folder
    steam_workshop_paths = [
        steam_path / "workshop" / "content" / "4000",
        steam_path / "workshop" / "downloads" / "4000",
        steam_path / "workshop" / "temp" / "4000",
        steam_path / "downloading" / "4000",
        steam_path / "download" / "4000"
    ]
    
    print("\nChecking Steam workshop paths...")
    for workshop_path in steam_workshop_paths:
        if workshop_path.exists():
            print(f"\nFound Steam workshop path: {workshop_path}")
            # Add the full path directly instead of trying to make it relative
            gmod_relative_paths.append(str(workshop_path))
            
    # Also add any detected Steam library workshop paths
    for drive in get_available_drives():
        steam_library = Path(drive) / "SteamLibrary" / "steamapps"
        if steam_library.exists():
            additional_paths = [
                steam_library / "workshop" / "content" / "4000",
                steam_library / "workshop" / "downloads" / "4000",
                steam_library / "workshop" / "temp" / "4000",
                steam_library / "downloading" / "4000",
                steam_library / "download" / "4000"
            ]
            for path in additional_paths:
                if path.exists():
                    print(f"\nFound additional workshop path: {path}")
                    gmod_relative_paths.append(str(path))
    
    # Convert relative paths to absolute paths using detected Garry's Mod location
    print("\nChecking Garry's Mod workshop locations...")
    checked_paths = set()  # Keep track of checked paths to avoid duplicates
    
    for path_str in gmod_relative_paths:
        try:
            # If it's already an absolute path, use it directly
            if ":" in path_str:  # Windows drive letter check
                path = Path(path_str)
            else:
                # Otherwise treat it as relative to gmod_path
                path = gmod_path / Path(path_str)
                
            # Handle wildcard paths
            if "*" in str(path):
                base_path = path.parent
                if base_path.exists():
                    print(f"\nSearching wildcard path: {base_path}")
                    for item in base_path.iterdir():
                        if item.is_dir() and str(item) not in checked_paths:
                            checked_paths.add(str(item))
                            process_workshop_path(item, vpk_files, vpk_patterns, stats)
            else:
                if path.exists() and str(path) not in checked_paths:
                    checked_paths.add(str(path))
                    process_workshop_path(path, vpk_files, vpk_patterns, stats)
        except Exception as e:
            print(f"  ✗ Error processing path {path_str}: {e}")

    # Add function to process workshop paths
    def process_workshop_path(path, vpk_files, vpk_patterns, stats):
        """Process a workshop path for content."""
        print(f"\nSearching workshop content: {path}")
        try:
            # Check if this is a workshop content folder
            is_workshop = "workshop" in str(path).lower()
            
            # Search for all relevant file types
            for pattern in vpk_patterns:
                try:
                    # Search recursively with progress tracking
                    found_files = list(path.rglob(pattern))
                    if found_files:
                        print(f"  Found {len(found_files)} {pattern} files")
                        for found_file in found_files:
                            if found_file not in vpk_files:
                                vpk_files.append(found_file)
                                if is_workshop:
                                    stats['workshop_items'] += 1
                                print(f"  ✓ Found {'workshop ' if is_workshop else ''}file: {found_file.name}")
                                
                                # Check GMA files for additional content
                                if pattern == "*.gma":
                                    try:
                                        with open(found_file, 'rb') as f:
                                            header = f.read(4096)
                                            if b'.bsp' in header or b'.vpk' in header:
                                                print(f"    [!] GMA file may contain additional content: {found_file.name}")
                                    except Exception as e:
                                        print(f"    [-] Could not read GMA header: {e}")
                except Exception as e:
                    print(f"  ✗ Error searching pattern {pattern}: {e}")
        except Exception as e:
            print(f"  ✗ Error processing workshop path {path}: {e}")

    # Rest of the existing code...
    
    # Additional addon search locations
    addon_locations = [
        # Main addon locations
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "addons",
        Path(os.getenv('PROGRAMDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "addons",
        Path(os.getenv('PROGRAMFILES')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "addons",
        Path(os.getenv('PROGRAMFILES(X86)')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "addons",
        
        # Workshop addon locations
        Path(os.getenv('PROGRAMDATA')) / "Steam" / "workshop" / "content" / "4000",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "workshop" / "content" / "4000",
        Path(os.getenv('PROGRAMFILES')) / "Steam" / "steamapps" / "workshop" / "content" / "4000",
        Path(os.getenv('PROGRAMFILES(X86)')) / "Steam" / "steamapps" / "workshop" / "content" / "4000",
        
        # Additional addon paths
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "lua" / "autorun",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "lua" / "entities",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "lua" / "weapons",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "data" / "addons"
    ]
    
    # Patterns to search in addons
    addon_patterns = [
        "*.bsp",    # Maps
        "*.vpk",    # Valve pack files
        "*.gma",    # Garry's Mod addon files
        "*.vmt",    # Material files
        "*.vtf",    # Texture files
        "*.mdl",    # Model files
        "*.phy",    # Physics files
        "*.vtx",    # Vertex files
        "*.vvd",    # Vertex data
        "*.sw.vtx", # Studio vertex files
        "*.dx80.vtx",
        "*.dx90.vtx",
        "*.ain",    # AI node graph
        "*.nav",    # Navigation mesh
        "*.txt",    # Config files that might reference content
        "*.lua",    # Lua scripts that might reference content
        "manifest.txt",  # Addon manifests
        "addon.txt",     # Addon info
        "*.json"        # Addon metadata
    ]
    
    # Search addon locations
    print("\nSearching for content in addon locations...")
    for location in addon_locations:
        if location.exists():
            print(f"\nChecking addon location: {location}")
            try:
                # First check if this is a direct addon folder (contains addon.json or lua folder)
                is_addon = False
                if (location / "addon.json").exists() or (location / "lua").exists():
                    is_addon = True
                    print(f"  [+] Found direct addon at: {location}")
                
                # Search for all addon patterns
                for pattern in addon_patterns:
                    try:
                        # If it's a direct addon, search only this folder
                        if is_addon:
                            search_path = location
                        else:
                            # Otherwise search all subfolders
                            search_path = location
                        
                        # Search recursively
                        for found_file in search_path.rglob(pattern):
                            if found_file not in vpk_files:
                                vpk_files.append(found_file)
                                print(f"  [+] Found {pattern}: {found_file.name}")
                                
                                # If we find a GMA, try to peek inside it
                                if pattern == "*.gma":
                                    try:
                                        # Try to read the GMA header to find any embedded BSP or VPK files
                                        with open(found_file, 'rb') as f:
                                            header = f.read(4096)
                                            if b'.bsp' in header or b'.vpk' in header:
                                                print(f"    [!] GMA file may contain additional content: {found_file.name}")
                                    except Exception as e:
                                        print(f"    [-] Could not read GMA header: {e}")
                                        
                    except Exception as e:
                        print(f"  [-] Error searching pattern {pattern}: {e}")
                        
            except Exception as e:
                print(f"  [-] Error searching {location}: {e}")
        else:
            print(f"  [-] Location not found: {location}")

    # Additional BSP search locations
    bsp_locations = [
        # Workshop locations
        Path(os.getenv('PROGRAMDATA')) / "Steam" / "workshop" / "content" / "4000",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "workshop" / "content" / "4000",
        Path(os.getenv('PROGRAMFILES')) / "Steam" / "steamapps" / "workshop" / "content" / "4000",
        Path(os.getenv('PROGRAMFILES(X86)')) / "Steam" / "steamapps" / "workshop" / "content" / "4000",
        
        # Download locations
        Path(os.getenv('APPDATA')) / "gmod" / "garrysmod" / "downloads",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "download",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "downloads",
        
        # Cache locations
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "cache",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "downloading" / "4000",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "temp" / "4000",
        
        # Additional potential locations
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "maps",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "addons",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "download" / "maps",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "downloads" / "maps"
    ]
    
    # Search BSP locations
    print("\nSearching for BSP files in additional locations...")
    for location in bsp_locations:
        if location.exists():
            print(f"\nChecking location: {location}")
            try:
                # Search recursively for BSP files
                for bsp_file in location.rglob("*.bsp"):
                    if bsp_file not in vpk_files:
                        vpk_files.append(bsp_file)
                        print(f"  [+] Found BSP: {bsp_file.name}")
                
                # Also search for VPK files in these locations
                for vpk_file in location.rglob("*.vpk"):
                    if vpk_file not in vpk_files:
                        vpk_files.append(vpk_file)
                        print(f"  [+] Found VPK: {vpk_file.name}")
            except Exception as e:
                print(f"  [-] Error searching {location}: {e}")
        else:
            print(f"  [-] Location not found: {location}")

    # Common VPK locations for each game
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
            "garrysmod/data",
            "garrysmod/resource",  # Added resource directory
            "garrysmod/models",    # Added models directory
            "garrysmod/scenes",    # Added scenes directory
            "garrysmod/particles", # Added particles directory
            "bin",
            "sourceengine",
            "platform",
            "hl2",
            "cstrike",
            "tf",
            "portal",
            "episodic",
            "ep2",
            "left4dead2",
            "dod",
            "csgo",               # Added CSGO directory
            "insurgency",         # Added Insurgency directory
            "dayofdefeat",        # Added DoD directory
            "left4dead",          # Added L4D1 directory
            "portal2",            # Added Portal 2 directory
            "zps",                # Added Zombie Panic Source directory
            "synergy",           # Added Synergy directory
            "garrysmod/mounted",  # Add mounted content directory
            "garrysmod/mounted/*",  # Search all mounted subdirectories
            "garrysmod/mounted/css",
            "garrysmod/mounted/hl2",
            "garrysmod/mounted/tf2",
            "garrysmod/mounted/ep1",
            "garrysmod/mounted/ep2",
            "garrysmod/mounted/dods",
            "garrysmod/mounted/portal",
            "garrysmod/mounted/l4d",
            "garrysmod/mounted/l4d2",
            "garrysmod/mount", # Alternative mount directory
            "garrysmod/mount/*",
            "garrysmod/content", # Content directory
            "garrysmod/content/*",
            "garrysmod/base",   # Base content
            "garrysmod/base/*",
            "garrysmod/bin",    # Binary content that might have embedded files
            "garrysmod/bin/*",
            "garrysmod/custom/*",  # Custom content folder
            "garrysmod/gamemodes/*/content",  # Gamemode content
            "garrysmod/gamemodes/*/entities",  # Gamemode entities
            "garrysmod/gamemodes/*/materials", # Gamemode materials
            "garrysmod/gamemodes/*/models",    # Gamemode models
            "garrysmod/gamemodes/*/sound",     # Gamemode sounds
            "garrysmod/gamemodes/sandbox/entities", # Sandbox specific
            "garrysmod/gamemodes/terrortown/entities", # TTT specific
            "garrysmod/gamemodes/base",        # Base gamemode
            "garrysmod/download/materials/*",   # Downloaded materials
            "garrysmod/downloads/materials/*",  # Alternative downloads
            "garrysmod/cache/materials/*",      # Cached materials
            "garrysmod/materials_temp/*",       # Temporary materials
            "garrysmod/materials_backup/*",     # Backup materials
            "garrysmod/materials_workshop/*",   # Workshop materials
            "garrysmod/materials_user/*",       # User materials
            "garrysmod/materials_map/*",        # Map-specific materials
            "garrysmod/materials_addon/*",      # Addon materials
            "garrysmod/materials_server/*",     # Server materials
            "garrysmod/materials_download/*",   # Downloaded materials
            "garrysmod/maps",
            "garrysmod/download/maps",
            "garrysmod/downloads/maps",
            "garrysmod/cache/maps",
            "garrysmod/addons/*/maps",
            "garrysmod/workshop/*",
            "garrysmod/workshop/maps",
            "garrysmod/workshop/content",
            "garrysmod/workshop/downloaded",
            "garrysmod/workshop/temp",
            "garrysmod/workshop/cache",
            "garrysmod/workshop/extracted",
            "garrysmod/workshop/ugc",
            "garrysmod/cache/workshop",
            "garrysmod/download/workshop",
            "garrysmod/downloads/workshop",
            "garrysmod/addons/workshop",
            "garrysmod/workshop_temp",
            "garrysmod/workshop_cache",
            "garrysmod/workshop_downloads",
            "garrysmod/fastdl/maps",
            "garrysmod/fastdl/workshop",
            "garrysmod/downloadlists/maps",
            "garrysmod/downloadlists/workshop"
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
    
    # VPK patterns to search for
    vpk_patterns = [
        "*_dir.vpk",
        "*_000.vpk",
        "*_textures.vpk",
        "*_misc.vpk",
        "*_sound.vpk",     # Added sound VPK
        "*_models.vpk",    # Added models VPK
        "*_materials.vpk", # Added materials VPK
        "*_maps.vpk",      # Added maps VPK
        "*_particles.vpk", # Added particles VPK
        "*.vpk",
        "*.bsp",
        "*.gma",
        "*.ain",           # Added AI node graph files
        "*.nav",           # Added navigation mesh files
        "pak01_*.vpk",  # Source engine content packs
        "pak02_*.vpk",
        "pak03_*.vpk",
        "pak04_*.vpk",
        "texture*.vpk",
        "materials*.vpk",
        "content*.vpk",
        "custom*.vpk",
        "download*.vpk",
        "addon*.vpk",
        "*.vmt",        # Direct VMT files
        "*.vtf",        # Direct VTF files
        "*.gcf",        # Old Source engine content
        "*.ncf",        # Steam content format
        "*.zip",        # Compressed content
        "*.rar",        # Compressed content
        "*.7z",         # Compressed content
        "*.gma.dat",    # Garry's Mod addon data
        "*.vtf.bz2",      # Compressed VTF
        "*.vtf.gz",       # GZipped VTF
        "*.vtf.zip",      # Zipped VTF
        "*.vmt.bz2",      # Compressed VMT
        "*.vmt.gz",       # GZipped VMT
        "*.vmt.zip",      # Zipped VMT
        "texture_*.dat",  # Texture data files
        "materials.dat",  # Material data files
        "content.dat",    # Content data files
        "*.cache",        # Cache files that might contain textures
        "*.manifest",     # Manifest files that might reference textures
        "*.res",          # Resource files
        "*.lst",          # List files that might contain texture paths
        "*.txt",          # Text files that might contain texture paths
        "*.db",          # Database files that might contain texture info
        "*.bin"          # Binary files that might contain texture data
    ]

    # Additional search in Steam workshop cache
    workshop_cache_paths = [
        # Specific workshop cache path
        Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/cache/workshop"),
        
        # Standard workshop paths
        Path(os.getenv('PROGRAMDATA')) / "Steam" / "workshop" / "content" / "4000",
        Path(os.getenv('PROGRAMDATA')) / "Steam" / "workshop" / "downloads",
        Path(os.getenv('APPDATA')) / "gmod" / "garrysmod" / "downloads",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "workshop" / "content" / "4000",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "workshop" / "content" / "4000",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "cache",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "cache" / "workshop",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "common" / "GarrysMod" / "garrysmod" / "download",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "downloading" / "4000",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "shadercache" / "4000",
        Path(os.getenv('LOCALAPPDATA')) / "Steam" / "steamapps" / "temp" / "4000",
        Path(os.getenv('PROGRAMFILES')) / "Steam" / "steamapps" / "workshop" / "content" / "4000",
        Path(os.getenv('PROGRAMFILES(X86)')) / "Steam" / "steamapps" / "workshop" / "content" / "4000",
        
        # Additional workshop cache locations
        Path("J:/SteamLibrary/steamapps/workshop"),
        Path("J:/SteamLibrary/steamapps/workshop/content"),
        Path("J:/SteamLibrary/steamapps/workshop/downloads"),
        Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/cache"),
        Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/download/workshop"),
        Path("J:/SteamLibrary/steamapps/common/GarrysMod/garrysmod/downloads/workshop")
    ]

    # Search workshop cache paths with enhanced logging
    print("\nSearching workshop cache locations...")
    for cache_path in workshop_cache_paths:
        if cache_path.exists():
            print(f"\nChecking workshop cache: {cache_path}")
            try:
                # First check if this is a workshop content folder
                is_workshop = False
                if "workshop" in str(cache_path).lower():
                    is_workshop = True
                    print(f"  [+] Found workshop content at: {cache_path}")
                
                # Search for all patterns
                for pattern in vpk_patterns:
                    try:
                        # Search recursively
                        for found_file in cache_path.rglob(pattern):
                            if found_file not in vpk_files:
                                vpk_files.append(found_file)
                                if is_workshop:
                                    stats['workshop_items'] += 1
                                print(f"  ✓ Found {'workshop ' if is_workshop else ''}file: {found_file.name}")
                                
                                # If we find a GMA, try to peek inside it
                                if pattern == "*.gma":
                                    try:
                                        with open(found_file, 'rb') as f:
                                            header = f.read(4096)
                                            if b'.bsp' in header or b'.vpk' in header:
                                                print(f"    [!] GMA file may contain additional content: {found_file.name}")
                                    except Exception as e:
                                        print(f"    [-] Could not read GMA header: {e}")
                                        
                    except Exception as e:
                        print(f"  ✗ Error searching pattern {pattern}: {e}")
                        
            except Exception as e:
                print(f"  ✗ Error searching {cache_path}: {e}")
        else:
            print(f"  [-] Location not found: {cache_path}")

    # Search mounted game content
    mounted_games = {
        "240": "css",      # Counter-Strike: Source
        "220": "hl2",      # Half-Life 2
        "380": "ep1",      # Episode One
        "420": "ep2",      # Episode Two
        "440": "tf2",      # Team Fortress 2
        "300": "dods",     # Day of Defeat: Source
        "400": "portal",   # Portal
        "500": "l4d",      # Left 4 Dead
        "550": "l4d2",     # Left 4 Dead 2
        "620": "portal2"   # Portal 2
    }

    # Search through mounted game content
    steam_path = game_paths["GarrysMod"].parent.parent
    for app_id, game_dir in mounted_games.items():
        mounted_path = steam_path / "common" / game_dir
        if mounted_path.exists():
            print(f"\nChecking mounted content from {game_dir}")
            for pattern in vpk_patterns:
                try:
                    for found_file in mounted_path.rglob(pattern):
                        if found_file not in vpk_files:
                            vpk_files.append(found_file)
                            print(f"  ✓ Found mounted file: {found_file.name}")
                except Exception as e:
                    print(f"  ✗ Error searching mounted pattern {pattern}: {e}")

    # Process each game's paths
    for game, path in game_paths.items():
        print(f"\nProcessing game: {game}")
        print(f"Base path: {path}")
        
        if game == "GarrysMod":
            # Check workshop content with expanded search
            workshop_paths = [
                path.parent / "workshop" / "content" / "4000",
                path.parent / "workshop" / "content",
                path.parent / "workshop",
                path.parent / "workshop" / "temp",      # Added temp workshop files
                path.parent / "workshop" / "downloads"  # Added workshop downloads
            ]
            
            for workshop_path in workshop_paths:
                if workshop_path.exists():
                    print(f"\nChecking Workshop content: {workshop_path}")
                    for workshop_item in workshop_path.rglob("*"):
                        if workshop_item.is_dir():
                            print(f"  Checking workshop item: {workshop_item.name}")
                            for pattern in vpk_patterns:
                                for found_file in workshop_item.rglob(pattern):
                                    if found_file not in vpk_files:
                                        vpk_files.append(found_file)
                                        print(f"    ✓ Found file: {found_file.name}")
            
            # Check all possible addon locations with expanded paths
            addon_paths = [
                path / "garrysmod" / "addons",
                path / "garrysmod" / "download",
                path / "garrysmod" / "downloads",
                path / "garrysmod" / "cache",
                path / "garrysmod" / "lua" / "autorun",    # Added autorun scripts
                path / "garrysmod" / "lua" / "entities",   # Added entity scripts
                path / "garrysmod" / "lua" / "weapons",    # Added weapon scripts
                path / "garrysmod" / "data" / "maps",      # Added map data
                path / "garrysmod" / "downloadlists",      # Added download lists
                path / "garrysmod" / "materials" / "temp"  # Added temp materials
            ]
            
            for addon_path in addon_paths:
                if addon_path.exists():
                    print(f"\nChecking addon path: {addon_path}")
                    for pattern in vpk_patterns:
                        for found_file in addon_path.rglob(pattern):
                            if found_file not in vpk_files:
                                vpk_files.append(found_file)
                                print(f"  ✓ Found file: {found_file.name}")
            
            # Check maps folder for BSP files recursively
            maps_path = path / "garrysmod" / "maps"
            if maps_path.exists():
                print(f"\nChecking maps folder: {maps_path}")
                for bsp_file in maps_path.rglob("*.bsp"):
                    if bsp_file not in vpk_files:
                        vpk_files.append(bsp_file)
                        print(f"  ✓ Found BSP: {bsp_file.name}")
        
        # Check each possible VPK location for this game
        for loc in vpk_locations.get(game, []):
            vpk_dir = path / loc
            print(f"\n  Checking directory: {vpk_dir}")
            
            if vpk_dir.exists():
                found_in_dir = False
                for pattern in vpk_patterns:
                    try:
                        matches = list(vpk_dir.rglob(pattern))
                        if matches:
                            found_in_dir = True
                            for vpk_file in matches:
                                if vpk_file not in vpk_files:
                                    vpk_files.append(vpk_file)
                                    print(f"    ✓ Found: {vpk_file.name}")
                    except Exception as e:
                        print(f"    ✗ Error searching pattern {pattern}: {e}")
                
                if not found_in_dir:
                    print(f"    ✗ No files found")
            else:
                print(f"    ✗ Directory does not exist")
    
    print(f"\nTotal files found: {len(vpk_files)} (VPK + BSP + GMA)")
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
    """Create folder structure for a given path."""
    # Sanitize the path first
    file_path = sanitize_path(file_path)
    
    # Remove 'materials/' from the start of the path if it exists
    file_path = file_path.lstrip('/')
    if file_path.lower().startswith('materials/'):
        file_path = file_path[len('materials/'):]
    
    # Convert to Path object for proper path handling
    full_path = Path(base_path) / file_path
    
    try:
        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return str(full_path)
    except Exception as e:
        print(f"  Warning: Could not create directory structure for {file_path}: {e}")
        return None

def create_vmt_content(vtf_path):
    """Create the content for a VMT file based on the VTF path."""
    # Remove 'materials/' from the start of the path if it exists
    texture_path = vtf_path.lstrip('/')
    if texture_path.lower().startswith('materials/'):
        texture_path = texture_path[len('materials/'):]
    
    # Remove .vtf extension if present
    texture_path = texture_path.replace('.vtf', '')
    
    # Skip patterns for non-weapon items
    skip_patterns = [
        'hands/', 'models/hands/', 'c_arms', 'c_hands', 'v_hands', '/arms/', '/sleeve',
        'effects/', 'sprites/', 'beam', 'glow', 'light', 'spark', 'flash', 'muzzle', 'smoke', 'fire', 'explosion',
        'vgui/', 'scope/', 'crosshairs/', '/hud/', '/gui/', '/screen',
        'tool', 'entities/'
    ]
    
    # Check if this is a texture we should skip
    if any(x in texture_path.lower() for x in skip_patterns):
        return (None, 'skipped')
    
    # Check for weapon textures
    texture_lower = texture_path.lower()
    
    # Debug print for weapon textures
    if any(x in texture_lower for x in ['weapons/', 'models/weapons/', 'v_weapons', 'w_weapons', 'c_weapons']):
        print(f"\nFound weapon texture: {texture_path}")
        
        # Determine weapon category
        for category, info in WEAPON_COLORS.items():
            if info['enabled']:
                for pattern in info['patterns']:
                    if pattern in texture_lower:
                        print(f"  Matched {category} pattern: {pattern}")
                        # Create colored weapon VMT that works for both view and world models
                        return (f'''VertexLitGeneric
{{
    "$basetexture" "{texture_path}"
    "$color" "{info['color']}"
    "$color2" "{info['color']}"
    "$selfillum" 1
    "$selfillumtint" "{info['color']}"
    "$model" 1
    "$halflambert" 0
    "$nocull" 1
    "$translucent" 0
    "$ignorez" 0
    "$vertexcolor" 1
    "$noalphamod" 1
    "$additive" 0
    "$envmap" ""
    "$envmaptint" "[0 0 0]"
    "$envmapcontrast" 0
    "$envmapsaturation" 0
    "$envmapfresnel" 0
    "$envmapfresnelminmaxexp" "[0 0 0]"
    "$phong" 0
    "$phongexponent" 0
    "$phongboost" 0
    "$phongfresnelranges" "[0 0 0]"
    "$rimlight" 0
    "$rimlightexponent" 0
    "$rimlightboost" 0
    "$rimmask" 0
    "$rimlighttint" "{info['color']}"
    "$rimlightfresnelminmaxexp" "[0 0 0]"
    "$rimlightalbedowrap" 0
    "$ambientocclusion" 0
    "$ambientoccltexture" "{texture_path}"
    "$ambientocclcolor" "{info['color']}"
    "$detail" "{texture_path}"
    "$detailscale" 1
    "$detailblendfactor" 1
    "$detailblendmode" 6
    "$alpha" 1
}}''', category)
        
        print(f"  No matching category found, using default color")
        # Default yellow for unrecognized weapons with same enhanced parameters
        return (f'''VertexLitGeneric
{{
    "$basetexture" "{texture_path}"
    "$color" "{DEFAULT_WEAPON_COLOR}"
    "$color2" "{DEFAULT_WEAPON_COLOR}"
    "$selfillum" 1
    "$selfillumtint" "{DEFAULT_WEAPON_COLOR}"
    "$model" 1
    "$halflambert" 0
    "$nocull" 1
    "$translucent" 0
    "$ignorez" 0
    "$vertexcolor" 1
    "$noalphamod" 1
    "$additive" 0
    "$envmap" ""
    "$envmaptint" "[0 0 0]"
    "$envmapcontrast" 0
    "$envmapsaturation" 0
    "$envmapfresnel" 0
    "$envmapfresnelminmaxexp" "[0 0 0]"
    "$phong" 0
    "$phongexponent" 0
    "$phongboost" 0
    "$phongfresnelranges" "[0 0 0]"
    "$rimlight" 0
    "$rimlightexponent" 0
    "$rimlightboost" 0
    "$rimmask" 0
    "$rimlighttint" "{DEFAULT_WEAPON_COLOR}"
    "$rimlightfresnelminmaxexp" "[0 0 0]"
    "$rimlightalbedowrap" 0
    "$ambientocclusion" 0
    "$ambientoccltexture" "{texture_path}"
    "$ambientocclcolor" "{DEFAULT_WEAPON_COLOR}"
    "$detail" "{texture_path}"
    "$detailscale" 1
    "$detailblendfactor" 1
    "$detailblendmode" 6
    "$alpha" 1
}}''', 'weapon_other')
    
    # Create transparent VMT for everything else
    if ENABLE_TRANSPARENCY:
        return (f'''LightmappedGeneric
{{
    "$basetexture" "{texture_path}"
    "$translucent" 1
    "$ignorez" 1
    "$alpha" {TRANSPARENCY_ALPHA}
}}''', 'transparent')
    else:
        return (f'''LightmappedGeneric
{{
    "$basetexture" "{texture_path}"
}}''', 'normal')

class BSPParser:
    """Simple BSP parser to extract texture paths."""
    HEADER_LUMPS = 64
    LUMP_TEXDATA = 2
    LUMP_TEXDATA_STRING_DATA = 43
    LUMP_TEXDATA_STRING_TABLE = 44

    def __init__(self, bsp_path):
        self.bsp_path = bsp_path
        self.texture_paths = set()

    def read_lump_info(self, bsp_file, lump_id):
        """Read lump information from BSP header."""
        bsp_file.seek(8 + lump_id * 16)  # Skip ident and version, then locate lump
        offset, length = struct.unpack("ii", bsp_file.read(8))  # Read offset and length
        return offset, length

    def extract_texture_paths(self):
        """Extract texture paths from BSP file."""
        try:
            with open(self.bsp_path, "rb") as bsp_file:
                # Memory map the file for faster reading
                with mmap.mmap(bsp_file.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    # Read string data
                    string_data_offset, string_data_length = self.read_lump_info(bsp_file, self.LUMP_TEXDATA_STRING_DATA)
                    string_data = mm[string_data_offset:string_data_offset + string_data_length]
                    
                    # Read string table
                    string_table_offset, string_table_length = self.read_lump_info(bsp_file, self.LUMP_TEXDATA_STRING_TABLE)
                    string_table = mm[string_table_offset:string_table_offset + string_table_length]
                    
                    # Extract strings from the string table
                    for i in range(0, string_table_length, 4):
                        if i + 4 <= string_table_length:
                            string_offset = struct.unpack("i", string_table[i:i+4])[0]
                            if string_offset < string_data_length:
                                # Read until null terminator
                                end = string_offset
                                while end < string_data_length and string_data[end] != 0:
                                    end += 1
                                texture_path = string_data[string_offset:end].decode('ascii', errors='ignore')
                                
                                # Clean and validate the texture path
                                texture_path = texture_path.strip()
                                if texture_path and not texture_path.startswith("TOOLSTEXTURE"):
                                    # Add .vtf extension if not present
                                    if not texture_path.lower().endswith('.vtf'):
                                        texture_path += ".vtf"
                                    # Ensure it starts with materials/
                                    if not texture_path.lower().startswith('materials/'):
                                        texture_path = f"materials/{texture_path}"
                                    self.texture_paths.add(texture_path)
            
            return list(self.texture_paths)
        except Exception as e:
            print(f"  ✗ Error parsing BSP file: {e}")
            return []

def process_vpk_file(vpk_file):
    """Process a single VPK or BSP file and return found texture paths."""
    texture_paths = []
    try:
        print(f"\nProcessing: {vpk_file}")
        
        # Handle BSP files
        if vpk_file.suffix.lower() == '.bsp':
            print("  BSP file detected - extracting embedded textures...")
            try:
                bsp = BSPParser(vpk_file)
                bsp_textures = bsp.extract_texture_paths()
                texture_count = len(bsp_textures)
                texture_paths.extend(bsp_textures)
                print(f"  [+] Extracted {texture_count} texture paths from BSP")
                if texture_count > 0:
                    print("  Sample textures found:")
                    for texture in sorted(bsp_textures)[:5]:  # Show first 5 textures
                        print(f"    - {texture}")
                    if texture_count > 5:
                        print(f"    ... and {texture_count - 5} more")
            except Exception as e:
                print(f"  [X] Error processing BSP file: {e}")
            return texture_paths

        # Skip VMT files
        if vpk_file.suffix.lower() == '.vmt':
            return texture_paths

        # Handle VPK files
        try:
            # Try opening with standard VPK format
            pak = vpk.open(str(vpk_file))
            
            # Process standard VPK format
            texture_count = 0
            total_files = len(pak)
            print(f"  Total files in VPK: {total_files}")
            
            for filepath in pak:
                if filepath.lower().endswith('.vtf'):  # Only looking for VTF files now
                    texture_paths.append(filepath)
                    texture_count += 1
                    
                    # Show progress every 1000 textures
                    if texture_count % 1000 == 0:
                        print(f"  ⋯ Found {texture_count} textures so far...")
            
            print(f"  ✓ Completed: Found {texture_count} textures")
            
        except Exception as e:
            # Try reading as a raw binary file if VPK reading fails
            print("  ℹ Attempting to read as legacy/raw format...")
            try:
                with open(vpk_file, 'rb') as f:
                    # Read file and look for .vtf file signatures
                    data = f.read()
                    
                    # Find all occurrences of .vtf in the binary data
                    pos = 0
                    while True:
                        pos = data.find(b'.vtf', pos)
                        if pos == -1:
                            break
                            
                        # Look backwards for potential start of path (up to 256 chars)
                        start = max(0, pos - 256)
                        path_data = data[start:pos + 4]
                        
                        # Try to extract valid path
                        try:
                            path_str = path_data.decode('ascii', errors='ignore')
                            # Clean up the path string
                            path_str = ''.join(c for c in path_str if c.isprintable() or c in '/\\')
                            path_parts = path_str.split('materials/')
                            if len(path_parts) > 1:
                                clean_path = 'materials/' + path_parts[-1]
                                if clean_path.endswith('.vtf'):
                                    texture_paths.append(clean_path)
                        except:
                            pass
                        pos += 4
                    
                    print(f"  ✓ Found {len(texture_paths)} texture paths in legacy/raw format")
            except Exception as e2:
                print(f"  ✗ Error reading file: {e2}")

        return texture_paths
    except Exception as e:
        print(f"  ✗ Error processing {vpk_file}: {e}")
        return texture_paths

def extract_gma_textures(gmod_path, gmad_exe=None, output_dir="texture_output"):
    """Extract textures from GMod .gma files, logging details."""
    texture_paths = []
    addon_dir = gmod_path / "garrysmod" / "addons"
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    print(f"\nProcessing GMod addons in: {addon_dir}")

    if not gmad_exe or not Path(gmad_exe).exists():
        print("  Gmad Extractor not provided or invalid. Skipping addon extraction.")
        return texture_paths

    if addon_dir.exists():
        gma_files = list(addon_dir.glob("*.gma"))
        print(f"  Found {len(gma_files)} .gma files.")
        for gma_file in gma_files:
            print(f"    Extracting: {gma_file}")
            extract_path = output_path / gma_file.stem
            try:
                subprocess.run([gmad_exe, "extract", "-file", str(gma_file), "-out", str(extract_path)], check=True)
                print(f"      Extracted to: {extract_path}")
                texture_count = 0
                for root, _, files in os.walk(extract_path):
                    for file in files:
                        if file.endswith(".vtf") or file.endswith(".vmt"):
                            full_path = str(Path(root) / file)
                            texture_paths.append(full_path)
                            texture_count += 1
                print(f"      Found {texture_count} textures in {gma_file}")
            except subprocess.CalledProcessError as e:
                print(f"      Failed to extract {gma_file}: {e}")
            except Exception as e:
                print(f"      Error processing {gma_file}: {e}")
    else:
        print(f"  Warning: {addon_dir} does not exist.")
    return texture_paths

def create_sound_script():
    """Create a custom sound script for C4 bomb."""
    sound_script = '''// Custom sound script for C4
"C4.Plant"
{
    "channel"       "CHAN_WEAPON"
    "volume"       "1.0"
    "soundlevel"   "SNDLVL_140dB"
    "pitch"        "95,105"
    
    "wave"    "weapons/c4/c4_plant.wav"
}

"C4.PlantSound"
{
    "channel"       "CHAN_WEAPON"
    "volume"       "1.0"
    "soundlevel"   "SNDLVL_140dB"
    "pitch"        "95,105"
    
    "wave"    "weapons/c4/c4_plant.wav"
}

"C4.ExplodeWarning"
{
    "channel"       "CHAN_VOICE"
    "volume"       "1.0"
    "soundlevel"   "SNDLVL_140dB"
    "pitch"        "95,105"
    
    "wave"    "weapons/c4/c4_beep1.wav"
}'''
    return sound_script

def setup_custom_sounds(gmod_path):
    """Set up custom sounds for C4."""
    print("\n=== Creating Custom Sounds ===")
    
    # Define paths
    sound_script_path = gmod_path / "garrysmod" / "scripts" / "game_sounds_custom.txt"
    sound_folder = gmod_path / "garrysmod" / "sound"
    c4_folder = sound_folder / "weapons" / "c4"
    backup_folder = sound_folder / "BACKUP_BEFORE_SCREAMING"
    
    # Create backup of original sounds
    if c4_folder.exists() and not backup_folder.exists():
        try:
            import shutil
            print("Creating backup of original sounds...")
            shutil.copytree(c4_folder, backup_folder)
            print(f"[+] Original sounds backed up to: {backup_folder}")
        except Exception as e:
            print(f"[-] Error creating sound backup: {e}")
            return None

    # Create necessary directories
    os.makedirs(c4_folder, exist_ok=True)
    
    # Define the pain sounds we'll use
    pain_sounds = {
        "c4_plant.wav": "male_scream.wav",  # For planting
        "c4_beep1.wav": "male_scream.wav",  # For beeping
        "c4_beep2.wav": "male_scream.wav",  # Alternative beep
        "c4_explode1.wav": "male_scream.wav"  # For explosion
    }
    
    # Create a very loud scream WAV file
    def create_loud_scream():
        """Create a very loud scream WAV file from male01 pain sound."""
        try:
            # Copy the male01 pain sound from HL2 directory
            hl2_sound = gmod_path / "garrysmod" / "sound" / "vo" / "npc" / "male01" / "pain07.wav"
            if hl2_sound.exists():
                import shutil
                scream_path = c4_folder / "male_scream.wav"
                shutil.copy2(hl2_sound, scream_path)
                print(f"[+] Created scream sound from: {hl2_sound}")
                return True
        except Exception as e:
            print(f"[-] Error creating scream sound: {e}")
        return False

    # Create the scream sound
    if not create_loud_scream():
        print("[-] Failed to create scream sound file")
        return None

    # Replace all C4 sounds with our scream
    print("\nReplacing C4 sounds...")
    for original, replacement in pain_sounds.items():
        try:
            source = c4_folder / replacement
            target = c4_folder / original
            import shutil
            shutil.copy2(source, target)
            print(f"[+] Replaced {original}")
        except Exception as e:
            print(f"[-] Error replacing {original}: {e}")
            return None

    # Create or update the sound script
    try:
        os.makedirs(os.path.dirname(sound_script_path), exist_ok=True)
        with open(sound_script_path, "w", encoding='utf-8') as f:
            f.write(create_sound_script())
        print(f"\n[+] Created custom sound script at: {sound_script_path}")
    except Exception as e:
        print(f"[-] Error creating sound script: {e}")
        return None

    # Return a dictionary with all the relevant paths
    return {
        'script_path': sound_script_path,
        'backup_path': backup_folder,
        'c4_folder': c4_folder
    }

def main():
    try:
        # Check and install dependencies first
        check_and_install_dependencies()
        
        # Try importing required packages
        try:
            global vpk
            import vpk
        except ImportError:
            print("\n[X] Error: Required module 'vpk' is not installed.")
            print("Since SKIP_DEPENDENCIES is True, you'll need to install it manually.")
            print("\nTo install manually, run these commands in your terminal:")
            print("  pip install python-valve")
            print("\nOr set SKIP_DEPENDENCIES = False at the top of the script to auto-install.")
            return
        
        texture_paths = set()  # Using a set to remove duplicates
        
        # Statistics tracking
        stats = {
            'vpk_count': 0,
            'bsp_count': 0,
            'vpk_textures': 0,
            'bsp_textures': 0,
            'workshop_items': 0,
            'custom_maps': 0
        }
        
        print("\n=== Texture Extraction Tool ===")
        print("Starting texture extraction process...")

        # Find Steam path
        steam_path = find_steam_path()
        if not steam_path:
            print("\nFatal Error: Could not find Steam installation. Please specify paths manually.")
            return

        print(f"\n[+] Using Steam installation at: {steam_path}")

        # Find game paths
        print("\n=== Game Detection ===")
        game_paths = find_game_paths(steam_path)
        
        if not game_paths:
            print("\nError: No supported games found.")
            print("Please verify game installations and try again.")
            return

        # Find Garry's Mod path specifically
        if "GarrysMod" not in game_paths:
            print("\nError: Garry's Mod installation not found!")
            return
        
        gmod_path = game_paths["GarrysMod"]
        gmod_materials = gmod_path / "garrysmod" / "materials"
        backup_folder = gmod_materials / "BACKUP_BEFORE_TRANSPARENT"

        # Set up custom sounds and get paths
        sound_paths = None
        if ENABLE_CUSTOM_SOUNDS:
            sound_paths = setup_custom_sounds(gmod_path)
            if not sound_paths:
                print("\nWarning: Failed to set up custom sounds. Continuing with texture processing...")
        
        print(f"\nFound {len(game_paths)} game(s):")
        for game, path in game_paths.items():
            print(f"  [+] {game}: {path}")

        # Create backup of existing materials if needed
        if gmod_materials.exists() and not backup_folder.exists():
            print("\n=== Creating Backup ===")
            print(f"Creating backup of existing materials in: {backup_folder}")
            try:
                import shutil
                shutil.copytree(gmod_materials, backup_folder)
                print("[+] Backup created successfully")
            except Exception as e:
                print(f"[-] Error creating backup: {e}")
                return

        # Find and process VPK files
        vpk_files = find_vpk_files(game_paths)
        
        if vpk_files:
            print("\n=== Processing Files ===")
            print(f"Processing {len(vpk_files)} files...")
            
            for i, file_path in enumerate(vpk_files, 1):
                print(f"\n[File {i}/{len(vpk_files)}]")
                
                # Track statistics
                if file_path.suffix.lower() == '.bsp':
                    stats['bsp_count'] += 1
                    if 'workshop' in str(file_path).lower():
                        stats['workshop_items'] += 1
                    else:
                        stats['custom_maps'] += 1
                else:
                    stats['vpk_count'] += 1
                
                new_textures = process_vpk_file(file_path)
                
                # Update texture statistics
                if file_path.suffix.lower() == '.bsp':
                    stats['bsp_textures'] += len(new_textures)
                else:
                    stats['vpk_textures'] += len(new_textures)
                
                texture_paths.update(new_textures)
                print(f"Total unique textures found so far: {len(texture_paths)}")
        else:
            print("\n[-] No files found to process!")
            return

        # Create VMTs in Garry's Mod materials folder
        if texture_paths:
            print(f"\n=== Creating VMT Files ===")
            print(f"Creating VMT files in: {gmod_materials}")
            
            # Save list of processed textures for reference
            desktop_path = os.path.expanduser("~/Desktop")
            paths_file = os.path.join(desktop_path, "processed_textures.txt")
            with open(paths_file, "w", encoding='utf-8') as f:
                for path in sorted(texture_paths):
                    f.write(path + "\n")
            print(f"[+] Saved texture list to: {paths_file}")
            
            # Create VMTs
            created_count = 0
            skipped_count = 0
            transparent_count = 0
            normal_count = 0
            weapon_counts = {}
            error_count = 0
            
            # Initialize weapon counts based on enabled categories
            if ENABLE_WEAPON_COLORS:
                for category in WEAPON_COLORS:
                    if WEAPON_COLORS[category]['enabled']:
                        weapon_counts[category] = 0
                weapon_counts['weapon_other'] = 0
            
            for vtf_path in sorted(texture_paths):
                try:
                    # Create the VMT path by replacing .vtf with .vmt
                    vmt_path = vtf_path.replace('.vtf', '.vmt')
                    full_path = create_folder_structure(gmod_materials, vmt_path)
                    
                    # Skip if path creation failed
                    if full_path is None:
                        error_count += 1
                        if error_count % 10 == 0:  # Log every 10th error
                            print(f"  Encountered {error_count} path creation errors...")
                        continue
                    
                    # Get VMT content and type
                    vmt_content, vmt_type = create_vmt_content(vtf_path)
                    
                    # Skip if None is returned
                    if vmt_content is None:
                        skipped_count += 1
                        if skipped_count % 100 == 0:
                            print(f"  Skipped {skipped_count} VMT files...")
                        continue
                    
                    # Create the VMT file
                    try:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(vmt_content)
                        created_count += 1
                        
                        # Track type counts
                        if vmt_type == 'transparent':
                            transparent_count += 1
                        elif vmt_type == 'normal':
                            normal_count += 1
                        elif vmt_type in weapon_counts:
                            weapon_counts[vmt_type] += 1
                        
                        if created_count % 100 == 0:
                            print(f"  Created {created_count} VMT files...")
                    except Exception as e:
                        error_count += 1
                        print(f"  [-] Error creating VMT for {vmt_path}: {e}")
                except Exception as e:
                    error_count += 1
                    print(f"  [-] Unexpected error processing {vtf_path}: {e}")
                    continue
            
            # Print final summary
            print("\n=== Final Summary ===")
            print("Files Processed:")
            print(f"  > VPK Files: {stats['vpk_count']}")
            print(f"  > BSP Maps: {stats['bsp_count']}")
            print(f"    * Workshop Items: {stats['workshop_items']}")
            print(f"    * Custom Maps: {stats['custom_maps']}")
            print("\nTextures Found:")
            print(f"  > From VPK files: {stats['vpk_textures']}")
            print(f"  > From BSP maps: {stats['bsp_textures']}")
            print(f"  > Total unique textures: {len(texture_paths)}")
            
            if ENABLE_WEAPON_COLORS:
                print("\nWeapons Modified:")
                for category, count in weapon_counts.items():
                    if category == 'weapon_other':
                        print(f"  > Other Weapons ({DEFAULT_WEAPON_COLOR_NAME}): {count}")
                    else:
                        print(f"  > {category.capitalize()}s ({WEAPON_COLORS[category]['name']}): {count}")
            
            print("\nOther Modifications:")
            if ENABLE_TRANSPARENCY:
                print(f"  > Transparent Objects: {transparent_count}")
            else:
                print(f"  > Normal Objects: {normal_count}")
            print(f"  > Skipped: {skipped_count}")
            print(f"  > Errors encountered: {error_count}")
            print(f"  > Total Modified: {created_count}")
            print("\nOutput:")
            print(f"  > Location: {gmod_materials}")
            print(f"  > Backup: {backup_folder}")
            print(f"  > Texture list: {paths_file}")
            if sound_paths:
                print(f"  > Custom sounds: {sound_paths['script_path']}")
                print(f"  > Sound backup: {sound_paths['backup_path']}")
            print("\n[i] Restart Garry's Mod to see the changes!")
            
        else:
            print("\n[-] No textures were found to process.")

    except Exception as e:
        print(f"\n[X] An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[X] Process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[X] An unexpected error occurred: {e}")
        print("If this persists, please report the issue.")
        sys.exit(1)