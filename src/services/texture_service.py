"""
Texture Service for Texture Extractor
Handles VMT file creation and management
"""

import os
import logging
import subprocess
from pathlib import Path
import win32security
import win32api
import win32con

class TextureService:
    """Service for creating and managing VMT files."""
    
    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config
        self.texture_quality = config.get("TEXTURE_QUALITY", {})
        self.transparency = config.get("TRANSPARENCY", {})
        self.prop_shader = config.get("PROP_SHADER", {})
        self.skip_patterns = config.get("SKIP_PATTERNS", {})
        self.weapon_colors = config.get("WEAPON_COLORS", {})
        
        # Use DELETION config key to match the settings dialog
        self.delete_patterns = config.get("DELETION", {})
        logging.debug(f"TextureService initialized with deletion settings: {self.delete_patterns}")
    
    def create_vmt_content(self, vtf_path: str):
        """Create VMT content for a VTF texture."""
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
    
            # If it's a weapon, apply coloring without transparency
            if is_weapon:
                # Determine weapon category for coloring
                color = '[1 1 1]'  # Default white
                for category, config in self.weapon_colors.items():
                    if config.get('enabled', False):  # Only check enabled categories
                        if any(pattern.lower() in path_lower for pattern in config.get('patterns', [])):
                            color = config.get('color', '[1 1 1]')
                            logging.debug(f"Applied {config.get('name', 'Unknown')} color {color} to {base_path}")
                            break
    
                return (f'''"UnlitGeneric"
{{
    "$basetexture"    "{base_path}"
    "$ignorez"        1
    "$vertexcolor"    1
    "$vertexalpha"    1
    "$nolod"        "1"
    "$color2"    "{color}"
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
    "$alpha" "{self.transparency.get('effect_alpha', 0.5)}"
}}''', 'transparent')
            else:
                # Default transparency for other textures
                return (f'''UnlitGeneric
{{
    "$basetexture" "{base_path}"
    "$translucent" "1"
    "$alpha" "{self.transparency.get('default_alpha', 0.45)}"
}}''', 'normal')
                
        except Exception as e:
            logging.error(f"Error creating VMT content for {vtf_path}: {e}")
            return None, None
    
    def should_delete_vmt(self, vtf_path: str) -> bool:
        """Determine if a VMT file should be deleted based on patterns."""
        if not self.delete_patterns.get('enabled', False):
            return False
            
        path_lower = vtf_path.lower()
        
        for category, config in self.delete_patterns.get('categories', {}).items():
            if config.get('enabled', False):
                if any(pattern.lower() in path_lower for pattern in config.get('patterns', [])):
                    logging.debug(f"VMT for {vtf_path} marked for deletion (matches {category} pattern)")
                    return True
                    
        return False
    
    def sanitize_path(self, path: str) -> str:
        """Sanitize file path by removing invalid characters and handling special cases."""
        try:
            # Remove any quotes from the path
            path = path.replace('"', '').replace("'", '')
            
            # Remove any parameters that might have been accidentally included
            if '{' in path:
                path = path.split('{')[0].strip()
                
            # Remove null characters and non-printable characters
            path = ''.join(char for char in path if char.isprintable() and char != '\0')
            
            # Replace invalid Windows filename characters
            invalid_chars = '<>:"|?*'
            for char in invalid_chars:
                path = path.replace(char, '_')
                
            # Normalize slashes
            path = path.replace('\\', '/').strip('/')
            
            # Remove any duplicate slashes
            while '//' in path:
                path = path.replace('//', '/')
                
            # Ensure path only contains ASCII characters
            path = path.encode('ascii', errors='ignore').decode('ascii')
            
            return path
            
        except Exception:
            return None  # Return None if path cannot be sanitized
    
    def create_folder_structure(self, base_path: str, file_path: str) -> str:
        """Create folder structure for a given path with robust permission handling."""
        # Sanitize the path first
        file_path = self.sanitize_path(file_path)
        
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
            return None
        except Exception as e:
            logging.error(f"Error creating directory structure: {e}")
            return None
    
        return str(full_path)
    
    def create_vmt_file(self, vmt_path: str, content: str) -> bool:
        """Create a VMT file with robust permission handling."""
        try:
            # Create the directory structure first
            vmt_dir = os.path.dirname(vmt_path)
            if not os.path.exists(vmt_dir):
                result = self.create_folder_structure(vmt_dir, "")
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
