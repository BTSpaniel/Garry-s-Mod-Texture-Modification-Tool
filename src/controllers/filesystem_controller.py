"""
Filesystem Controller for Texture Extractor
Handles finding Steam and game paths, VPK files, and file operations
"""

import os
import string
import logging
import threading
import concurrent.futures
from pathlib import Path
import vpk
import time

# VPK patterns and locations
VPK_PATTERNS = [
    "*_dir.vpk",
    "*_000.vpk",
    "*_textures.vpk",
    "*_misc.vpk",
    "*.vpk",
    "*.bsp",
    "*.gma"
]

VPK_LOCATIONS = {
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

def get_available_drives():
    """Get all available drives on Windows, checking from Z to A."""
    drives = []
    for letter in reversed(string.ascii_uppercase):  # Start from Z and go backwards
        drive = f"{letter}:"
        if os.path.exists(f"{drive}\\"):
            drives.append(drive)
    return drives

def find_steam_path():
    """Find Steam installation path using registry, with fallback paths."""
    print("\n=== Steam Path Detection ===")
    print("Searching for Steam installation...")
    steam_path = None

    # Get all available drives except C: (already in reverse order from Z to A)
    drives = [f"{letter}:" for letter in reversed(string.ascii_uppercase) 
             if letter != 'C' and os.path.exists(f"{letter}:")]
    
    print(f"\nSearching drives in order: {', '.join(drives)}")
    
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

def find_vpk_files(game_paths, gui_callback=None, should_continue=None, task_progress_callback=None):
    """Find VPK files for Source games using multi-threading for faster scanning."""
    print("\n=== VPK File Detection ===")
    vpk_files = []
    found_files_lock = threading.Lock()  # Lock for thread-safe list operations
    last_gui_update = time.time()
    update_interval = 0.1  # Update GUI every 100ms
    
    def should_stop():
        """Check if we should stop processing."""
        return should_continue and not should_continue()
    
    def update_gui_found(count, force=False):
        """Update GUI with current file count, but limit update frequency."""
        nonlocal last_gui_update
        current_time = time.time()
        
        # Only update GUI if forced or enough time has passed since last update
        if force or (current_time - last_gui_update >= update_interval):
            if gui_callback:
                gui_callback(count)
            else:
                print(f"Found {count} VPK files so far")
            last_gui_update = current_time
    
    def scan_directory(directory, patterns, description=""):
        """Scan a directory for VPK files using the given patterns."""
        found = []
        if not directory.exists():
            return found
            
        print(f"Scanning: {description} {directory}")
        
        try:
            # First, do a quick scan for common VPK files without recursion
            for pattern in patterns[:4]:  # First 4 patterns are the most common
                if should_stop():
                    return found
                    
                try:
                    # Use glob instead of rglob for the initial scan (much faster)
                    for found_file in directory.glob(pattern):
                        if should_stop():
                            return found
                            
                        if found_file.is_file():
                            found.append(found_file)
                except Exception as e:
                    print(f"Error in quick scan with pattern {pattern}: {e}")
            
            # Then do a more thorough recursive scan
            for pattern in patterns:
                if should_stop():
                    return found
                    
                try:
                    for found_file in directory.rglob(pattern):
                        if should_stop():
                            return found
                            
                        if found_file.is_file() and found_file not in found:
                            found.append(found_file)
                except Exception as e:
                    print(f"Error in deep scan with pattern {pattern}: {e}")
                    
        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")
            
        return found
    
    def process_scan_results(results):
        """Process scan results and update the GUI."""
        nonlocal vpk_files
        with found_files_lock:
            for file_list in results:
                for file in file_list:
                    if file not in vpk_files:
                        vpk_files.append(file)
            update_gui_found(len(vpk_files))
    
    # Check if Garry's Mod exists
    gmod_path = game_paths.get("GarrysMod")
    if not gmod_path:
        print("Error: Garry's Mod path not found!")
        return vpk_files
    
    # Prepare scan tasks
    scan_tasks = []
    
    # Process each game's paths
    for game, path in game_paths.items():
        if should_stop():
            return vpk_files
            
        print(f"\nProcessing game: {game}")
        print(f"Base path: {path}")
        
        # Add game-specific locations
        for loc in VPK_LOCATIONS.get(game, []):
            vpk_dir = path / loc
            if vpk_dir.exists():
                scan_tasks.append((vpk_dir, VPK_PATTERNS, f"{game} - {loc}"))
        
        # Special handling for Garry's Mod workshop content
        if game == "GarrysMod":
            workshop_paths = [
                path.parent / "workshop" / "content" / "4000",  # Most common workshop path
                path.parent / "workshop" / "content"
            ]
            
            for workshop_path in workshop_paths:
                if workshop_path.exists():
                    scan_tasks.append((workshop_path, VPK_PATTERNS, "Workshop content"))
    
    # Use ThreadPoolExecutor for parallel scanning
    max_workers = min(32, len(scan_tasks) + 1)  # Limit max workers
    print(f"Starting parallel scan with {max_workers} workers for {len(scan_tasks)} directories")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scan tasks
        future_to_task = {executor.submit(scan_directory, *task): task for task in scan_tasks}
        
        # Process results as they complete
        completed = 0
        total_tasks = len(future_to_task)
        
        # Notify about total tasks if callback provided
        if task_progress_callback:
            task_progress_callback(0, total_tasks)
        
        for future in concurrent.futures.as_completed(future_to_task):
            if should_stop():
                executor.shutdown(wait=False)
                break
                
            try:
                result = future.result()
                process_scan_results([result])
            except Exception as e:
                task = future_to_task[future]
                print(f"Error scanning {task[2]}: {e}")
            
            completed += 1
            
            # Update task progress if callback provided
            if task_progress_callback:
                task_progress_callback(completed, total_tasks)
                
            if gui_callback:
                # Update progress in status message
                gui_callback(len(vpk_files))
                print(f"Completed {completed}/{total_tasks} scan tasks")
    
    # Final update
    update_gui_found(len(vpk_files), force=True)
    print(f"Found {len(vpk_files)} VPK files total")
    return vpk_files

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
