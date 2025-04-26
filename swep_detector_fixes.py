"""
This file contains fixes for the SWEP detector module.
Copy and paste these methods into the SWEPDetector class to fix the indentation and parsing issues.
"""

def _process_binary_content(self, file_path: Path) -> Tuple[Set[str], Set[str], Dict, bool]:
    """Process binary content from a file that might be a binary Lua file."""
    texture_refs = set()
    model_refs = set()
    detected_sweps = {}
    
    try:
        with open(file_path, 'rb') as f:
            binary_content = f.read()
            
        # Try to decode binary content
        decoded_content = ""
        try:
            # Try UTF-8 decoding first
            decoded_content = binary_content.decode('utf-8', errors='ignore')
        except Exception:
            # Fallback to latin-1 which should always work
            decoded_content = binary_content.decode('latin-1', errors='ignore')
            
        # Check if it contains weapon-related content
        if self._is_likely_swep(decoded_content):
            # Extract texture and model references
            texture_refs.update(self._extract_texture_references_worker(decoded_content))
            model_refs.update(self._extract_model_references_worker(decoded_content))
            
            # Look for SWEP definitions
            swep_matches = list(re.finditer(r'SWEP\s*=\s*\{([^}]+)\}', decoded_content, re.DOTALL))
            weapons_register_matches = list(re.finditer(r'weapons\.Register\s*\(\s*([^,]+),\s*["\']([^"\']*)["\'](.*?)\)', decoded_content, re.DOTALL))
            
            # Process SWEP definitions
            for match in swep_matches:
                try:
                    swep_table = match.group(1)
                    swep_info = self._parse_swep_table(swep_table)
                    
                    if not swep_info:
                        continue
                        
                    swep_name = swep_info.get('PrintName', 'Unknown')
                    swep_class = file_path.stem
                    swep_base = swep_info.get('Base', 'weapon_base')
                    swep_category = swep_info.get('Category', '')
                    
                    # Determine gamemode
                    gamemode = self._detect_gamemode(swep_base, swep_category, decoded_content)
                    
                    # Store SWEP info
                    detected_sweps[swep_class] = {
                        'name': swep_name,
                        'class': swep_class,
                        'base': swep_base,
                        'category': swep_category,
                        'gamemode': gamemode,
                        'file': str(file_path),
                    }
                    
                    self.stats['sweps_detected'] += 1
                    logging.info(f"Detected binary SWEP: {swep_class}")
                except Exception as e:
                    logging.debug(f"Error parsing binary SWEP table: {e}")
            
            # Process weapons.Register calls
            for match in weapons_register_matches:
                try:
                    table_var = match.group(1).strip()
                    weapon_class = match.group(2).strip()
                    
                    # Try to find the table definition
                    table_def_pattern = f"{table_var}\\s*=\\s*\\{{([^}}]+)\\}}"
                    table_matches = list(re.finditer(table_def_pattern, decoded_content, re.DOTALL))
                    
                    if table_matches:
                        table_content = table_matches[0].group(1)
                        weapon_info = self._parse_swep_table(table_content)
                        
                        if not weapon_info:
                            continue
                            
                        weapon_name = weapon_info.get('PrintName', 'Unknown')
                        weapon_base = weapon_info.get('Base', 'weapon_base')
                        weapon_category = weapon_info.get('Category', '')
                        
                        # Determine gamemode
                        gamemode = self._detect_gamemode(weapon_base, weapon_category, decoded_content)
                        
                        # Store weapon info
                        detected_sweps[weapon_class] = {
                            'name': weapon_name,
                            'class': weapon_class,
                            'base': weapon_base,
                            'category': weapon_category,
                            'gamemode': gamemode,
                            'file': str(file_path),
                            'registration': 'weapons.Register'
                        }
                        
                        self.stats['sweps_detected'] += 1
                        logging.info(f"Detected binary weapons.Register: {weapon_class}")
                except Exception as e:
                    logging.debug(f"Error parsing binary weapons.Register: {e}")
            
            return texture_refs, model_refs, detected_sweps, True
    except Exception as e:
        logging.error(f"Error processing binary content from {file_path}: {e}")
    
    return texture_refs, model_refs, detected_sweps, False

def _parse_swep_table(self, table_content: str) -> Dict[str, str]:
    """Extract key information from a SWEP table definition."""
    swep_info = {}
    
    # Extract key properties using regex
    # Look for PrintName = "...", Base = "...", etc.
    property_pattern = r'([A-Za-z0-9_]+)\s*=\s*["\'](.+?)["\']'
    for match in re.finditer(property_pattern, table_content, re.DOTALL):
        key = match.group(1).strip()
        value = match.group(2).strip()
        
        if key and value:
            swep_info[key] = value
            
            # Track model references
            if key.lower() in ['model', 'worldmodel', 'viewmodel']:
                if value and isinstance(value, str):
                    self.model_references.add(value)
                    self.stats['models_found'] += 1
    
    # Also look for numeric properties like Slot = 1
    numeric_pattern = r'([A-Za-z0-9_]+)\s*=\s*([0-9]+)'
    for match in re.finditer(numeric_pattern, table_content, re.DOTALL):
        key = match.group(1).strip()
        value = match.group(2).strip()
        
        if key and value:
            swep_info[key] = value
    
    return swep_info

def _extract_texture_references_worker(self, content: str) -> Set[str]:
    """Extract texture references from content."""
    texture_refs = set()
    
    # Extract texture paths from Material() calls
    material_matches = re.finditer(r'Material\(\s*["\']([^"\']*)["\'](\s*,\s*[^)]*)?\)', content, re.DOTALL)
    for mat_match in material_matches:
        texture_path = mat_match.group(1)
        if texture_path:
            texture_refs.add(texture_path)
            self.stats['textures_found'] += 1
    
    # Extract VMT/VTF references
    vmt_matches = re.finditer(r'["\'](materials/[^"\']*.(?:vmt|vtf))["\'](\s*,\s*[^)]*)?', content, re.DOTALL)
    for vmt_match in vmt_matches:
        texture_path = vmt_match.group(1)
        if texture_path:
            texture_refs.add(texture_path)
            self.stats['textures_found'] += 1
    
    return texture_refs

def _extract_model_references_worker(self, content: str) -> Set[str]:
    """Extract model references from content."""
    model_refs = set()
    
    # Extract model paths from Model() calls and direct references
    model_matches = re.finditer(r'["\']((models|.*\.mdl)[^"\']*)["\']', content, re.DOTALL)
    for model_match in model_matches:
        model_path = model_match.group(1)
        if model_path and '.mdl' in model_path.lower():
            model_refs.add(model_path)
            self.stats['models_found'] += 1
    
    return model_refs
