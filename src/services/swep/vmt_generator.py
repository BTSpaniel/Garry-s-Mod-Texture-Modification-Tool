"""
VMT Generator Module for Source Engine Asset Manager

A simplified version of texture service that only handles VMT file creation
for the SWEP detector module.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Tuple, Union, List


class VMTGenerator:
    """Simplified service for creating VMT files for SWEPs."""
    
    def __init__(self, config: Dict = None):
        """Initialize with configuration."""
        self.config = config or {}
        self.transparency = self.config.get("TRANSPARENCY", {})
        self.prop_shader = self.config.get("PROP_SHADER", {})
        self.skip_patterns = self.config.get("SKIP_PATTERNS", {})
        self.weapon_colors = self.config.get("WEAPON_COLORS", {})
        self.delete_patterns = self.config.get("DELETE_PATTERNS", {})
    
    def create_vmt_content(self, vtf_path: str) -> Tuple[str, str]:
        """
        Create VMT content for a VTF texture.
        
        Args:
            vtf_path: Path to the VTF file
            
        Returns:
            Tuple of (vmt_content, shader_type)
        """
        try:
            # Remove 'materials/' from the start if present
            if vtf_path.lower().startswith('materials/'):
                vtf_path = vtf_path[len('materials/'):]
                
            # Get the base path without extension
            base_path = vtf_path[:-4] if vtf_path.lower().endswith('.vtf') else vtf_path
            path_lower = base_path.lower()
    
            # Check if it's a weapon texture
            weapon_patterns = [
                '/weapons/', 'models/weapons', '/w_', '/v_', '/c_',
                'weapon_', 'models/v_', 'models/w_', 'models/c_'
            ]
            is_weapon = any(pattern in path_lower for pattern in weapon_patterns)
    
            # If it's a weapon, apply enhanced visibility and category-based coloring
            if is_weapon:
                # Determine weapon category for coloring
                color = '[1.2 1.2 1.2]'  # Default: slightly brighter than normal
                glow = '[0.3 0.3 0.3]'    # Default: subtle glow
                
                for category, config in self.weapon_colors.items():
                    if config.get('enabled', False):  # Only check enabled categories
                        if any(pattern.lower() in path_lower for pattern in config.get('patterns', [])):
                            color = config.get('color', '[1.2 1.2 1.2]')
                            glow = config.get('glow', '[0.3 0.3 0.3]')
                            logging.debug(f"Applied {config.get('name', 'Unknown')} color {color} and glow {glow} to {base_path}")
                            break
    
                # Enhanced weapon VMT with glow and improved visibility
                return (f'''"UnlitGeneric"
{{
    "$basetexture"    "{base_path}"
    "$ignorez"        1
    "$vertexcolor"    1
    "$vertexalpha"    1
    "$nolod"        "1"
    "$color2"    "{color}"
    "$selfillum"      1
    "$selfillumtint"  "{glow}"
}}''', 'weapon')
    
            # Check if it's a prop texture
            is_prop = self.prop_shader.get('enabled', False) and any(
                pattern in path_lower for pattern in self.prop_shader.get('patterns', [])
            )
            
            # If it's a prop and prop shader changes are enabled, use LightmappedGeneric shader
            if is_prop:
                if self.prop_shader.get('use_lightmapped', True):
                    return (f'''"LightmappedGeneric"
{{
    // Original shader: BaseTimesLightmap
$basetexture "{base_path}"
$alpha {self.prop_shader.get('alpha', 0.9)}
}}''', 'prop')
                else:
                    return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
    "$translucent" "1"
    "$alpha" "{self.prop_shader.get('alpha', 0.9)}"
}}''', 'prop')
            
            # Check if the texture should use normal VMT based on skip patterns
            if self.skip_patterns.get('enabled', False):
                for category, config in self.skip_patterns.get('patterns', {}).items():
                    if config.get('enabled', False):
                        if any(pattern.lower() in path_lower for pattern in config.get('patterns', [])):
                            return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
}}''', 'normal')
            
            # For all other textures, keep the transparency effects
            if any(x in path_lower for x in ['glass', 'window']):
                # Extra transparent texture
                return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
    "$translucent" "1"
    "$alpha" "0.4"
}}''', 'transparent')
            
            # Default to VertexLitGeneric with transparency
            alpha = self.transparency.get('default_alpha', 0.45)
            return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
    "$translucent" "1"
    "$alpha" "{alpha}"
}}''', 'default')
            
        except Exception as e:
            logging.error(f"Error creating VMT content: {e}")
            # Fallback to basic VMT
            return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
}}''', 'fallback')
    
    def create_vmt_file(self, vmt_path: str, content: str) -> bool:
        """
        Create a VMT file.
        
        Args:
            vmt_path: Path to the VMT file to create
            content: Content to write to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create the directory structure first
            vmt_dir = os.path.dirname(vmt_path)
            if not os.path.exists(vmt_dir):
                os.makedirs(vmt_dir, exist_ok=True)
    
            # Write the file
            with open(vmt_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return True
            
        except Exception as e:
            logging.error(f"Error creating VMT file: {e}")
            return False
            
    def should_delete_vmt(self, vtf_path: str) -> bool:
        """
        Determine if a VMT file should be deleted based on patterns.
        
        Args:
            vtf_path: Path to the VTF file
            
        Returns:
            True if the VMT should be deleted, False otherwise
        """
        if not self.delete_patterns.get('enabled', False):
            return False
            
        path_lower = vtf_path.lower()
        
        for category, config in self.delete_patterns.get('categories', {}).items():
            if config.get('enabled', False):
                if any(pattern.lower() in path_lower for pattern in config.get('patterns', [])):
                    logging.debug(f"VMT for {vtf_path} marked for deletion (matches {category} pattern)")
                    return True
                    
        return False
        
    def batch_delete_vmts(self, vmt_paths: List[Tuple[str, str]]) -> int:
        """
        Delete multiple VMT files in batch based on patterns.
        
        Args:
            vmt_paths: List of tuples (vmt_path, vtf_path)
            
        Returns:
            Number of VMT files deleted
        """
        delete_count = 0
        for vmt_path, vtf_path in vmt_paths:
            if self.should_delete_vmt(vtf_path):
                try:
                    if os.path.exists(vmt_path):
                        os.remove(vmt_path)
                        delete_count += 1
                except Exception as e:
                    logging.error(f"Error deleting VMT {vmt_path}: {e}")
        return delete_count
