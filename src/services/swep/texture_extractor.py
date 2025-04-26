"""
Texture Extractor Module for SWEP Detector

This module handles the extraction of texture references from SWEP definitions.
"""

import re
from pathlib import Path
from typing import Set, Dict, List, Optional, Union


class TextureExtractor:
    """Handles extraction of texture references from SWEP definitions."""
    
    def __init__(self, config: Dict = None):
        """
        Initialize the TextureExtractor.
        
        Args:
            config: Configuration dictionary with extractor settings
        """
        self.config = config or {}
        self.texture_patterns = self.config.get('weapon_texture_patterns', [
            'weapons/',
            'v_',
            'w_',
            'c_',
            'hands/',
            'arms/',
            'models/weapons',
            'materials/weapons',
            'materials/models/weapons',
            'materials/vgui',
            'SetMaterial(',
            'SetSubMaterial(',
            'Material('
        ])
    
    def extract_texture_references(self, content: str) -> Set[str]:
        """
        Extract texture references from content.
        
        Args:
            content: Content to extract texture references from
            
        Returns:
            Set of texture references
        """
        texture_refs = set()
        
        # Look for material paths in various formats
        patterns = [
            r'materials/([^\s"\']+)\.vtf',  # Direct VTF references
            r'materials/([^\s"\']+)\.vmt',  # Direct VMT references
            r'Material\(["\'](.*?)["\']\)',  # Material() function calls
            r'SetMaterial\(["\'](.*?)["\']\)',  # SetMaterial() function calls
            r'SetSubMaterial\(\d+,\s*["\'](.*?)["\']\)',  # SetSubMaterial() function calls
            r'["\'](materials/.*?)["\']',  # Quoted material paths
            r'["\'](models/.*?/.*?)["\']'  # Model paths that might have materials
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                path = match.group(1).strip() if len(match.groups()) > 0 else ""
                if path:
                    # Normalize path format
                    if not path.startswith('materials/') and not path.startswith('models/'):
                        if 'models/' in path.lower():
                            # This is likely a model path
                            path = path[path.lower().find('models/'):]
                        else:
                            # Assume it's a material path
                            path = f"materials/{path}"
                    
                    # Clean up path
                    path = path.replace('\\', '/')
                    
                    # Add to texture references
                    texture_refs.add(path)
        
        return texture_refs
    
    def extract_from_swep_table(self, table_content: str) -> Set[str]:
        """
        Extract texture references from a SWEP table.
        
        Args:
            table_content: SWEP table content
            
        Returns:
            Set of texture references
        """
        texture_refs = set()
        
        # Look for material properties
        material_keys = ['Material', 'VMaterial', 'WMaterial', 'Skin', 'Icon']
        
        # String pattern for properties like Material = "models/weapons/v_pistol"
        string_pattern = r'([A-Za-z0-9_]+)\s*=\s*["\']([^"\']*)["\']'
        for match in re.finditer(string_pattern, table_content, re.DOTALL):
            key = match.group(1).strip()
            value = match.group(2).strip()
            
            if key in material_keys or 'material' in key.lower() or 'texture' in key.lower():
                if value:
                    # Normalize path format
                    if not value.startswith('materials/') and not value.startswith('models/'):
                        if 'models/' in value.lower():
                            # This is likely a model path
                            value = value[value.lower().find('models/'):]
                        else:
                            # Assume it's a material path
                            value = f"materials/{value}"
                    
                    # Clean up path
                    value = value.replace('\\', '/')
                    
                    # Add to texture references
                    texture_refs.add(value)
        
        # Look for table assignments like Materials = {"path1", "path2"}
        table_pattern = r'([A-Za-z0-9_]+)\s*=\s*{([^}]*)}'
        for match in re.finditer(table_pattern, table_content, re.DOTALL):
            key = match.group(1).strip()
            table_content = match.group(2).strip()
            
            if key.lower() in ['materials', 'textures', 'skins']:
                # Extract string values from the table
                table_values = re.findall(r'["\'](.*?)["\']', table_content)
                for value in table_values:
                    if value:
                        # Normalize path format
                        if not value.startswith('materials/') and not value.startswith('models/'):
                            if 'models/' in value.lower():
                                # This is likely a model path
                                value = value[value.lower().find('models/'):]
                            else:
                                # Assume it's a material path
                                value = f"materials/{value}"
                        
                        # Clean up path
                        value = value.replace('\\', '/')
                        
                        # Add to texture references
                        texture_refs.add(value)
        
        # Look for function calls like SetMaterial("path")
        func_pattern = r'(?:self\.)?([A-Za-z0-9_]+)\s*\(\s*["\'](.*?)["\']'
        for match in re.finditer(func_pattern, table_content, re.DOTALL):
            func_name = match.group(1).strip().lower()
            value = match.group(2).strip()
            
            if func_name in ['setmaterial', 'setsubmaterial', 'setmodelmaterial'] and value:
                # Normalize path format
                if not value.startswith('materials/') and not value.startswith('models/'):
                    if 'models/' in value.lower():
                        # This is likely a model path
                        value = value[value.lower().find('models/'):]
                    else:
                        # Assume it's a material path
                        value = f"materials/{value}"
                
                # Clean up path
                value = value.replace('\\', '/')
                
                # Add to texture references
                texture_refs.add(value)
        
        return texture_refs
