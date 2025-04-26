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
