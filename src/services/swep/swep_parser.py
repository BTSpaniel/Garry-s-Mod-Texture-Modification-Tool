"""
SWEP Parser Module for SWEP Detector

This module handles the parsing of SWEP tables and extraction of SWEP information.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union

from .texture_extractor import TextureExtractor
from .model_extractor import ModelExtractor


class SWEPParser:
    """Handles parsing of SWEP tables and extraction of SWEP information."""
    
    def __init__(self, config: Dict = None):
        """
        Initialize the SWEPParser.
        
        Args:
            config: Configuration dictionary with parser settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize extractors
        self.texture_extractor = TextureExtractor(config)
        self.model_extractor = ModelExtractor(config)
    
    def parse_swep_table(self, table_content: str) -> Dict:
        """
        Extract key information from a SWEP table definition.
        
        Args:
            table_content: Content of the SWEP table
            
        Returns:
            Dictionary of SWEP information
        """
        swep_info = {}
        
        # Look for string properties like PrintName = "Weapon Name"
        string_pattern = r'([A-Za-z0-9_]+)\s*=\s*["\']([^"\']*)["\']'
        for match in re.finditer(string_pattern, table_content, re.DOTALL):
            key = match.group(1).strip()
            value = match.group(2).strip()
            
            if key and value:
                swep_info[key] = value
        
        # Also look for numeric properties like Slot = 1
        numeric_pattern = r'([A-Za-z0-9_]+)\s*=\s*([0-9]+)'
        for match in re.finditer(numeric_pattern, table_content, re.DOTALL):
            key = match.group(1).strip()
            value = match.group(2).strip()
            
            if key and value:
                swep_info[key] = value
        
        # Look for boolean properties like Automatic = true
        bool_pattern = r'([A-Za-z0-9_]+)\s*=\s*(true|false)'
        for match in re.finditer(bool_pattern, table_content, re.IGNORECASE | re.DOTALL):
            key = match.group(1).strip()
            value = match.group(2).strip().lower() == 'true'
            
            if key:
                swep_info[key] = value
        
        return swep_info
    
    def parse_lua_file(self, lua_file: Path) -> Tuple[Dict, Set[str], Set[str]]:
        """
        Parse a Lua file for SWEP information and references.
        
        Args:
            lua_file: Path to the Lua file
            
        Returns:
            Tuple of (detected_sweps, texture_refs, model_refs)
        """
        try:
            # Read the file content
            with open(lua_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check if this file contains SWEP definitions
            swep_patterns = [
                r'SWEP\.Base\s*=',
                r'SWEP\.PrintName\s*=',
                r'SWEP\.ViewModel\s*=',
                r'SWEP\.WorldModel\s*=',
                r'SWEP\.Primary\s*=',
                r'SWEP\.Secondary\s*=',
                r'weapons\.Register\(',
                r'scripted_weapon\s*=',
                r'WEAPON\.'
            ]
            
            is_swep_file = False
            for pattern in swep_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    is_swep_file = True
                    break
            
            if not is_swep_file:
                return {}, set(), set()
            
            # Extract texture references
            texture_refs = self.texture_extractor.extract_texture_references(content)
            
            # Extract model references
            model_refs = self.model_extractor.extract_model_references(content)
            
            # Extract SWEP information
            detected_sweps = {}
            
            # Look for SWEP table definitions
            swep_table_pattern = r'SWEP\.([A-Za-z0-9_]+)\s*=\s*([^;]+)'
            for match in re.finditer(swep_table_pattern, content, re.DOTALL):
                key = match.group(1).strip()
                value = match.group(2).strip()
                
                if key and value:
                    # Extract SWEP properties
                    if key in ['PrintName', 'Author', 'Category', 'Base', 'Slot', 'SlotPos']:
                        # Clean up value (remove quotes)
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Add to detected SWEPs
                        weapon_name = lua_file.stem
                        if weapon_name not in detected_sweps:
                            detected_sweps[weapon_name] = {}
                        
                        detected_sweps[weapon_name][key] = value
                    
                    # Extract model references from SWEP properties
                    if key in ['ViewModel', 'WorldModel']:
                        # Clean up value (remove quotes)
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        if value:
                            # Normalize path format
                            if not value.startswith('models/'):
                                value = f"models/{value}"
                            
                            # Clean up path
                            value = value.replace('\\', '/')
                            
                            # Add to model references
                            model_refs.add(value)
                            
                            # Add to detected SWEPs
                            weapon_name = lua_file.stem
                            if weapon_name not in detected_sweps:
                                detected_sweps[weapon_name] = {}
                            
                            detected_sweps[weapon_name][key] = value
            
            # Look for weapons.Register calls
            register_pattern = r'weapons\.Register\(\s*([^,]+),\s*["\'](.*?)["\']'
            for match in re.finditer(register_pattern, content, re.IGNORECASE):
                table_ref = match.group(1).strip()
                weapon_name = match.group(2).strip()
                
                if weapon_name and weapon_name not in detected_sweps:
                    detected_sweps[weapon_name] = {'RegisteredName': weapon_name}
                    
                    # Try to find the table definition
                    table_pattern = f"{table_ref}\s*=\s*{{([^}}]+)}}"
                    table_match = re.search(table_pattern, content, re.DOTALL)
                    if table_match:
                        table_content = table_match.group(1)
                        swep_info = self.parse_swep_table(table_content)
                        detected_sweps[weapon_name].update(swep_info)
                        
                        # Extract texture and model references from the table
                        table_texture_refs = self.texture_extractor.extract_from_swep_table(table_content)
                        table_model_refs = self.model_extractor.extract_from_swep_table(table_content)
                        
                        texture_refs.update(table_texture_refs)
                        model_refs.update(table_model_refs)
            
            return detected_sweps, texture_refs, model_refs
            
        except Exception as e:
            self.logger.debug(f"Lua file parsing failed for {lua_file.name}: {e}")
            return {}, set(), set()
    
    def detect_gamemode(self, base: str, category: str, content: str) -> str:
        """
        Detect which gamemode a weapon belongs to based on its properties and content.
        
        Args:
            base: Base weapon class
            category: Weapon category
            content: File content
            
        Returns:
            Detected gamemode
        """
        # Default gamemode
        gamemode = "sandbox"
        
        # Check for TTT-specific patterns
        ttt_patterns = [
            r'SWEP\.Kind\s*=\s*WEAPON_',
            r'SWEP\.CanBuy\s*=',
            r'ROLE_TRAITOR',
            r'ROLE_DETECTIVE',
            r'TTT\.',
            r'EquipMenuData'
        ]
        
        for pattern in ttt_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "ttt"
        
        # Check for DarkRP-specific patterns
        darkrp_patterns = [
            r'SWEP\.jobName\s*=',
            r'DarkRP\.',
            r'AddCustomShipment'
        ]
        
        for pattern in darkrp_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "darkrp"
        
        # Check for Murder-specific patterns
        murder_patterns = [
            r'SWEP\.IsMurdererWeapon\s*=',
            r'SWEP\.IsKnife\s*='
        ]
        
        for pattern in murder_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "murder"
        
        # Check for PropHunt-specific patterns
        prophunt_patterns = [
            r'SWEP\.IsPropHuntWeapon\s*=',
            r'TEAM_PROPS',
            r'TEAM_HUNTERS'
        ]
        
        for pattern in prophunt_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "prophunt"
        
        # Check base and category for hints
        if base:
            base_lower = base.lower()
            if 'ttt' in base_lower or 'terror' in base_lower:
                return "ttt"
            elif 'darkrp' in base_lower:
                return "darkrp"
            elif 'murder' in base_lower:
                return "murder"
            elif 'prophunt' in base_lower:
                return "prophunt"
        
        if category:
            category_lower = category.lower()
            if 'ttt' in category_lower or 'terror' in category_lower:
                return "ttt"
            elif 'darkrp' in category_lower:
                return "darkrp"
            elif 'murder' in category_lower:
                return "murder"
            elif 'prophunt' in category_lower:
                return "prophunt"
        
        return gamemode
