#!/usr/bin/env python3
"""
SWEP Analyzer for Garry's Mod
------------------------------
Scans Lua files from decoded .gma or Lua cache directories to identify and categorize SWEPs.
Detects various gamemode-specific weapons and extracts detailed information.
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
import concurrent.futures
import time

# Configuration
DEFAULT_GMOD_PATH = "J:/SteamLibrary/steamapps/common/GarrysMod"
MAX_WORKERS = 8  # Number of parallel workers for file processing

class SWEPAnalyzer:
    """Analyzes Garry's Mod Lua files to identify and categorize SWEPs."""
    
    def __init__(self, gmod_path: str = DEFAULT_GMOD_PATH, output_file: str = "swep_analysis.json"):
        self.gmod_path = Path(gmod_path)
        self.output_file = output_file
        self.sweps = {}
        self.scan_stats = {
            "files_scanned": 0,
            "sweps_found": 0,
            "gamemode_breakdown": {},
            "base_breakdown": {},
            "errors": 0
        }
        
        # Patterns for detecting SWEP definitions
        self.swep_patterns = [
            (r'SWEP\s*=\s*\{([^}]+)\}', 'SWEP table'),
            (r'weapons\.Register\s*\(\s*([^,]+),\s*["\'](["\']*)["\']', 'weapons.Register'),
            (r'scripted_ents\.Register\s*\(\s*([^,]+),\s*["\'](["\']*)["\']', 'scripted_ents.Register'),
            (r'DEFINE_BASECLASS\s*\(\s*["\'](["\']*)["\']\s*\)', 'DEFINE_BASECLASS'),
            (r'SWEP\.Base\s*=\s*["\'](["\']*)["\']', 'SWEP.Base'),
            (r'SWEP\.PrintName\s*=\s*["\'](["\']*)["\']', 'SWEP.PrintName')
        ]
        
        # Gamemode detection patterns
        self.gamemode_patterns = {
            'TTT': [
                r'weapon_tttbase', 
                r'weapon_tttbasegrenade', 
                r'terrortown', 
                r'"ttt"', 
                r'WEAPON_EQUIP'
            ],
            'DarkRP': [
                r'darkrp', 
                r'SWEP\.Category\s*=\s*"DarkRP"'
            ],
            'Zombie Survival': [
                r'weapon_zs_base', 
                r'zombiesurvival', 
                r'zombify'
            ],
            'Murder': [
                r'murder/murder/', 
                r'murder.*knife'
            ],
            'Prop Hunt': [
                r'ph_gun', 
                r'prophunt', 
                r'prop_hunt'
            ]
        }
    
    def scan_directories(self):
        """Scan all relevant Garry's Mod directories for Lua files."""
        lua_files = []
        
        # Define directories to scan
        scan_dirs = [
            # Main Lua directories
            self.gmod_path / "garrysmod" / "lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons",
            self.gmod_path / "garrysmod" / "lua" / "entities",
            
            # Addon directories
            self.gmod_path / "garrysmod" / "addons",
            
            # Cache directories
            self.gmod_path / "garrysmod" / "cache" / "lua",
            self.gmod_path / "garrysmod" / "cache" / "workshop"
        ]
        
        # Directly add known weapon files
        weapon_files = [
            # Standard HL2 weapons
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_fists.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_medkit.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_flechettegun.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_base.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_pistol.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_smg1.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_shotgun.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_357.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_ar2.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_crossbow.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_crowbar.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_stunstick.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_slam.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "weapon_rpg.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "gmod_camera.lua",
            self.gmod_path / "garrysmod" / "lua" / "weapons" / "gmod_tool.lua",
            
            # TTT weapons
            self.gmod_path / "garrysmod" / "gamemodes" / "terrortown" / "entities" / "weapons" / "weapon_ttt_base.lua",
            self.gmod_path / "garrysmod" / "gamemodes" / "terrortown" / "entities" / "weapons" / "weapon_ttt_confgrenade.lua",
            self.gmod_path / "garrysmod" / "gamemodes" / "terrortown" / "entities" / "weapons" / "weapon_ttt_knife.lua",
            self.gmod_path / "garrysmod" / "gamemodes" / "terrortown" / "entities" / "weapons" / "weapon_ttt_m16.lua",
            self.gmod_path / "garrysmod" / "gamemodes" / "terrortown" / "entities" / "weapons" / "weapon_ttt_smokegrenade.lua",
            
            # DarkRP weapons
            self.gmod_path / "garrysmod" / "gamemodes" / "darkrp" / "entities" / "weapons" / "keys.lua",
            self.gmod_path / "garrysmod" / "gamemodes" / "darkrp" / "entities" / "weapons" / "pocket.lua",
            self.gmod_path / "garrysmod" / "gamemodes" / "darkrp" / "entities" / "weapons" / "weapon_keypadchecker.lua",
            
            # Murder weapons
            self.gmod_path / "garrysmod" / "gamemodes" / "murder" / "entities" / "weapons" / "weapon_mu_knife.lua",
            self.gmod_path / "garrysmod" / "gamemodes" / "murder" / "entities" / "weapons" / "weapon_mu_magnum.lua",
            
            # Zombie Survival weapons
            self.gmod_path / "garrysmod" / "gamemodes" / "zombiesurvival" / "entities" / "weapons" / "weapon_zs_base.lua",
            
            # Prop Hunt weapons
            self.gmod_path / "garrysmod" / "gamemodes" / "prop_hunt" / "entities" / "weapons" / "weapon_ph_prop.lua"
        ]
        
        # Add existing weapon files to the scan list
        for weapon_file in weapon_files:
            if weapon_file.exists():
                lua_files.append(weapon_file)
        
        # Add Steam workshop content
        workshop_dirs = [
            Path("J:/SteamLibrary/steamapps/workshop/content/4000"),
            Path("C:/Program Files (x86)/Steam/steamapps/workshop/content/4000"),
            Path("D:/Steam/steamapps/workshop/content/4000"),
            Path("E:/Steam/steamapps/workshop/content/4000")
        ]
        
        # Add specific gamemode directories to search
        gamemode_dirs = [
            # TTT
            self.gmod_path / "garrysmod" / "gamemodes" / "terrortown" / "entities" / "weapons",
            self.gmod_path / "garrysmod" / "gamemodes" / "terrortown" / "entities" / "items",
            
            # DarkRP
            self.gmod_path / "garrysmod" / "gamemodes" / "darkrp" / "entities" / "weapons",
            self.gmod_path / "garrysmod" / "gamemodes" / "darkrp" / "entities" / "entities",
            
            # Murder
            self.gmod_path / "garrysmod" / "gamemodes" / "murder" / "entities" / "weapons",
            
            # Zombie Survival
            self.gmod_path / "garrysmod" / "gamemodes" / "zombiesurvival" / "entities" / "weapons",
            
            # Prop Hunt
            self.gmod_path / "garrysmod" / "gamemodes" / "prop_hunt" / "entities" / "weapons"
        ]
        
        # Add any existing gamemode directories
        for gamemode_dir in gamemode_dirs:
            if gamemode_dir.exists():
                scan_dirs.append(gamemode_dir)
        
        scan_dirs.extend([d for d in workshop_dirs if d.exists()])
        
        print(f"Scanning {len(scan_dirs)} directories for Lua files...")
        
        # Collect all Lua files from the directories
        for directory in scan_dirs:
            if not directory.exists():
                continue
                
            print(f"Scanning {directory}...")
            
            # Scan for Lua files
            for ext in ['.lua', '.lc', '.luac', '.txt', '.dat']:
                try:
                    lua_files.extend(list(directory.glob(f"**/*{ext}")))
                except Exception as e:
                    print(f"Error scanning {directory} for {ext} files: {e}")
            
            # Also scan for files without extensions that might be Lua files
            try:
                for file_path in directory.glob("**/*"):
                    if file_path.is_file() and not file_path.suffix and file_path not in lua_files:
                        lua_files.append(file_path)
            except Exception as e:
                print(f"Error scanning {directory} for extensionless files: {e}")
                
        # Specifically look for weapon files in addon directories
        if (self.gmod_path / "garrysmod" / "addons").exists():
            print("Scanning addons for weapon files...")
            try:
                # Look for files in weapon-related paths within addons
                weapon_paths = [
                    "**/weapons/*.lua",
                    "**/entities/weapons/*.lua",
                    "**/entities/*/weapon_*.lua",
                    "**/lua/weapons/*.lua",
                    "**/lua/autorun/weapons/*.lua",
                    "**/lua/*/weapons/*.lua",
                    "**/gamemodes/*/entities/weapons/*.lua"
                ]
                
                for pattern in weapon_paths:
                    addon_weapon_files = list((self.gmod_path / "garrysmod" / "addons").glob(pattern))
                    if addon_weapon_files:
                        print(f"Found {len(addon_weapon_files)} potential weapon files with pattern {pattern}")
                        lua_files.extend(addon_weapon_files)
            except Exception as e:
                print(f"Error scanning addons for weapon files: {e}")
        
        print(f"Found {len(lua_files)} potential Lua files to analyze")
        return lua_files
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single file for SWEP definitions."""
        results = {}
        
        try:
            # Skip very large files
            file_size = file_path.stat().st_size
            if file_size > 10 * 1024 * 1024:  # Skip files larger than 10MB
                return results
                
            # Special handling for weapon files
            if 'weapon_' in str(file_path).lower() or 'swep' in str(file_path).lower():
                print(f"Processing weapon file: {file_path}")
                
            # First try to read as binary, then convert to text
            try:
                with open(file_path, 'rb') as f:
                    binary_content = f.read()
                    
                # Check for Lua binary signatures
                is_binary_lua = False
                if binary_content.startswith(b'\x1bLua') or b'SWEP' in binary_content or b'weapons.Register' in binary_content:
                    is_binary_lua = True
                    
                # Convert to text for pattern matching
                content = binary_content.decode('utf-8', errors='ignore')
                
                # If it's a binary Lua file, print some debug info
                if is_binary_lua:
                    print(f"Found binary Lua file: {file_path}")
            except Exception as e:
                # Fallback to text reading if binary fails
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
            # Special case for weapon files - extract info even without full SWEP table
            if 'weapon_' in str(file_path).lower() or 'swep' in str(file_path).lower():
                swep_class = file_path.stem
                print_name_match = re.search(r'PrintName\s*=\s*["\'](.*?)["\'](,|\s|$)', content)
                base_match = re.search(r'Base\s*=\s*["\'](.*?)["\'](,|\s|$)', content)
                category_match = re.search(r'Category\s*=\s*["\'](.*?)["\'](,|\s|$)', content)
                
                if print_name_match or 'SWEP' in content or 'weapon' in swep_class.lower():
                    # This is likely a weapon file
                    gamemode = self._detect_gamemode(base_match.group(1) if base_match else '', 
                                                  category_match.group(1) if category_match else '', 
                                                  content)
                    
                    results[swep_class] = {
                        'name': print_name_match.group(1) if print_name_match else swep_class,
                        'class': swep_class,
                        'base': base_match.group(1) if base_match else 'weapon_base',
                        'category': category_match.group(1) if category_match else '',
                        'gamemode': gamemode,
                        'file': str(file_path),
                        'definition_type': 'weapon file'
                    }
            
            # Look for SWEP definitions
            for pattern, pattern_type in self.swep_patterns:
                if pattern_type == 'SWEP table':
                    # Find SWEP table definitions
                    for match in re.finditer(pattern, content, re.DOTALL):
                        swep_table = match.group(1)
                        swep_info = self._parse_swep_table(swep_table)
                        
                        if swep_info and 'PrintName' in swep_info:
                            swep_class = file_path.stem
                            gamemode = self._detect_gamemode(swep_info.get('Base', ''), 
                                                           swep_info.get('Category', ''), 
                                                           content)
                            
                            results[swep_class] = {
                                'name': swep_info['PrintName'],
                                'class': swep_class,
                                'base': swep_info.get('Base', 'weapon_base'),
                                'category': swep_info.get('Category', ''),
                                'gamemode': gamemode,
                                'file': str(file_path),
                                'definition_type': 'SWEP table'
                            }
                            
                elif pattern_type == 'weapons.Register':
                    # Find weapons.Register calls
                    for match in re.finditer(pattern, content, re.DOTALL):
                        table_var = match.group(1).strip()
                        weapon_class = match.group(2).strip()
                        
                        # Try to find the table definition
                        table_def_pattern = f"{table_var}\\s*=\\s*\\{{([^}}]+)\\}}"
                        table_matches = list(re.finditer(table_def_pattern, content, re.DOTALL))
                        
                        if table_matches:
                            table_content = table_matches[0].group(1)
                            weapon_info = self._parse_swep_table(table_content)
                            
                            if weapon_info and 'PrintName' in weapon_info:
                                gamemode = self._detect_gamemode(weapon_info.get('Base', ''), 
                                                               weapon_info.get('Category', ''), 
                                                               content)
                                
                                results[weapon_class] = {
                                    'name': weapon_info['PrintName'],
                                    'class': weapon_class,
                                    'base': weapon_info.get('Base', 'weapon_base'),
                                    'category': weapon_info.get('Category', ''),
                                    'gamemode': gamemode,
                                    'file': str(file_path),
                                    'definition_type': 'weapons.Register'
                                }
                
                elif pattern_type == 'scripted_ents.Register':
                    # Similar processing for scripted_ents.Register
                    for match in re.finditer(pattern, content, re.DOTALL):
                        table_var = match.group(1).strip()
                        entity_class = match.group(2).strip()
                        
                        # Check if this might be a weapon entity
                        if 'weapon' in entity_class.lower() or 'swep' in entity_class.lower():
                            table_def_pattern = f"{table_var}\\s*=\\s*\\{{([^}}]+)\\}}"
                            table_matches = list(re.finditer(table_def_pattern, content, re.DOTALL))
                            
                            if table_matches:
                                table_content = table_matches[0].group(1)
                                entity_info = self._parse_swep_table(table_content)
                                
                                if entity_info and 'PrintName' in entity_info:
                                    gamemode = self._detect_gamemode(entity_info.get('Base', ''), 
                                                                   entity_info.get('Category', ''), 
                                                                   content)
                                    
                                    results[entity_class] = {
                                        'name': entity_info['PrintName'],
                                        'class': entity_class,
                                        'base': entity_info.get('Base', 'weapon_base'),
                                        'category': entity_info.get('Category', ''),
                                        'gamemode': gamemode,
                                        'file': str(file_path),
                                        'definition_type': 'scripted_ents.Register'
                                    }
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            self.scan_stats["errors"] += 1
            
        return results
    
    def _parse_swep_table(self, table_content: str) -> Dict[str, str]:
        """Extract key information from a SWEP table definition."""
        result = {}
        
        # Extract PrintName - try different patterns to catch more cases
        print_name_patterns = [
            r'PrintName\s*=\s*["\']([^"\']*)["\'](,|\s|$)',
            r'PrintName\s*=\s*["\']([^"\']*)["\'](,|\s|\})',
            r'["\']PrintName["\'](\s*:\s*|\s*=\s*)["\']([^"\']*)["\'](,|\s|\})',
            r'PrintName\s*=\s*([^,\s\}]+)'  # Fallback for non-quoted names
        ]
        
        for pattern in print_name_patterns:
            print_name_match = re.search(pattern, table_content)
            if print_name_match:
                # The capture group might be different based on the pattern
                if len(print_name_match.groups()) > 1 and 'PrintName' in pattern:
                    result['PrintName'] = print_name_match.group(2)
                else:
                    result['PrintName'] = print_name_match.group(1)
                break
                
        # If we still don't have a PrintName, try a more aggressive approach
        if 'PrintName' not in result and 'name' in table_content.lower():
            name_match = re.search(r'["\']?name["\']?\s*[=:]\s*["\']([^"\']*)["\']', table_content, re.IGNORECASE)
            if name_match:
                result['PrintName'] = name_match.group(1)
        
        # Extract Base class
        base_match = re.search(r'Base\s*=\s*["\']([^"\']*)["\']', table_content)
        if base_match:
            result['Base'] = base_match.group(1)
            
        # Extract Category
        category_match = re.search(r'Category\s*=\s*["\']([^"\']*)["\']', table_content)
        if category_match:
            result['Category'] = category_match.group(1)
            
        # Extract other useful properties
        for prop in ['Slot', 'SlotPos', 'Author', 'Contact', 'Purpose', 'Instructions']:
            prop_match = re.search(f'{prop}\\s*=\\s*["\']([^"\']*)["\']', table_content)
            if prop_match:
                result[prop] = prop_match.group(1)
                
        return result
    
    def _detect_gamemode(self, base: str, category: str, content: str) -> str:
        """Detect which gamemode a weapon belongs to based on its properties and content."""
        content_lower = content.lower()
        file_path_lower = content_lower  # Also check the file path which might be in the content
        
        # Check for TTT
        ttt_indicators = ['ttt', 'terrortown', 'traitor', 'innocent', 'detective', 'weapon_ttt', 'WEAPON_EQUIP']
        for indicator in ttt_indicators:
            if indicator in content_lower:
                return 'TTT'
        if base and ('weapon_tttbase' in base or 'weapon_tttbasegrenade' in base):
            return 'TTT'
        
        # Check for DarkRP
        darkrp_indicators = ['darkrp', 'rp_', 'arrest', 'unarrest', 'wanted', 'police', 'mayor', 'gangster']
        for indicator in darkrp_indicators:
            if indicator in content_lower:
                return 'DarkRP'
        if category and 'darkrp' in category.lower():
            return 'DarkRP'
        
        # Check for Zombie Survival
        zs_indicators = ['zombiesurvival', 'zombify', 'undead', 'weapon_zs', 'zs_', 'zombie']
        for indicator in zs_indicators:
            if indicator in content_lower:
                return 'Zombie Survival'
        if base and 'weapon_zs_base' in base:
            return 'Zombie Survival'
        
        # Check for Murder
        murder_indicators = ['murder', 'mu_knife', 'mu_magnum', 'murderer', 'bystander']
        for indicator in murder_indicators:
            if indicator in content_lower:
                return 'Murder'
        
        # Check for Prop Hunt
        ph_indicators = ['prop_hunt', 'ph_', 'prophunt', 'ph_prop', 'ph_gun']
        for indicator in ph_indicators:
            if indicator in content_lower:
                return 'Prop Hunt'
        
        # Check for other common gamemodes
        if 'deathrun' in content_lower:
            return 'Deathrun'
        if 'jailbreak' in content_lower or 'jb_' in content_lower:
            return 'Jailbreak'
        if 'bhop' in content_lower:
            return 'Bunny Hop'
        if 'surf' in content_lower:
            return 'Surf'
        if 'cinema' in content_lower:
            return 'Cinema'
        if 'flood' in content_lower:
            return 'Flood'
        
        # Default to Sandbox if no specific gamemode detected
        if base and ('weapon_base' in base or 'gmod_base' in base):
            return 'Sandbox'
            
        return 'Sandbox'
    
    def run_analysis(self):
        """Run the full SWEP analysis process."""
        start_time = time.time()
        print("Starting SWEP analysis...")
        
        # Scan for Lua files
        lua_files = self.scan_directories()
        self.scan_stats["files_scanned"] = len(lua_files)
        
        # Process files in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_file = {executor.submit(self.analyze_file, file_path): file_path for file_path in lua_files}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    results = future.result()
                    self.sweps.update(results)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    self.scan_stats["errors"] += 1
                
                # Show progress
                completed += 1
                if completed % 1000 == 0 or completed == len(lua_files):
                    print(f"Processed {completed}/{len(lua_files)} files ({completed/len(lua_files)*100:.1f}%)")
        
        # Update statistics
        self.scan_stats["sweps_found"] = len(self.sweps)
        
        # Calculate gamemode breakdown
        gamemode_counts = {}
        base_counts = {}
        for swep_class, swep_info in self.sweps.items():
            gamemode = swep_info.get('gamemode', 'Unknown')
            base = swep_info.get('base', 'Unknown')
            
            gamemode_counts[gamemode] = gamemode_counts.get(gamemode, 0) + 1
            base_counts[base] = base_counts.get(base, 0) + 1
        
        self.scan_stats["gamemode_breakdown"] = gamemode_counts
        self.scan_stats["base_breakdown"] = base_counts
        
        # Save results to file
        self._save_results()
        
        # Print summary
        print("\nSWEP Analysis Complete")
        print(f"Total time: {time.time() - start_time:.2f} seconds")
        print(f"Files scanned: {self.scan_stats['files_scanned']}")
        print(f"SWEPs found: {self.scan_stats['sweps_found']}")
        print(f"Errors encountered: {self.scan_stats['errors']}")
        
        if self.sweps:
            print("\nGamemode breakdown:")
            for gamemode, count in sorted(gamemode_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {gamemode}: {count}")
            
            print("\nTop 10 base classes:")
            for base, count in sorted(base_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {base}: {count}")
                
            print("\nSample of detected SWEPs:")
            sample_count = min(10, len(self.sweps))
            for i, (swep_class, swep_info) in enumerate(list(self.sweps.items())[:sample_count]):
                print(f"  {i+1}. {swep_info.get('name', 'Unknown')} ({swep_class})")
                print(f"     Base: {swep_info.get('base', 'Unknown')}")
                print(f"     Gamemode: {swep_info.get('gamemode', 'Unknown')}")
                print(f"     File: {swep_info.get('file', 'Unknown')}")
                print()
            
        print(f"Full results saved to {self.output_file}")
    
    def _save_results(self):
        """Save the analysis results to a JSON file."""
        output_data = {
            "sweps": self.sweps,
            "stats": self.scan_stats,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Analyze Garry's Mod Lua files for SWEP definitions")
    parser.add_argument("--gmod-path", default=DEFAULT_GMOD_PATH, help="Path to Garry's Mod installation")
    parser.add_argument("--output", default="swep_analysis.json", help="Output JSON file")
    args = parser.parse_args()
    
    analyzer = SWEPAnalyzer(gmod_path=args.gmod_path, output_file=args.output)
    analyzer.run_analysis()

if __name__ == "__main__":
    main()
