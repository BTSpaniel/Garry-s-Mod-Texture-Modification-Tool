"""
Model Extractor Module for SWEP Detector

This module handles the extraction of model references from SWEP definitions.
"""

import re
from pathlib import Path
from typing import Set, Dict, List, Optional, Union


class ModelExtractor:
    """Handles extraction of model references from SWEP definitions."""
    
    def __init__(self, config: Dict = None):
        """
        Initialize the ModelExtractor.
        
        Args:
            config: Configuration dictionary with extractor settings
        """
        self.config = config or {}
        self.model_patterns = self.config.get('weapon_model_patterns', [
            'SWEP.ViewModel',
            'SWEP.WorldModel',
            'self.ViewModel',
            'self.WorldModel',
            '.ViewModel =',
            '.WorldModel =',
            ':SetModel',
            'SetModel(',
            'weapons/',
            'v_',
            'w_',
            'models/weapons',
            'models/v_',
            'models/w_',
            'models/c_'
        ])
    
    def extract_model_references(self, content: str) -> Set[str]:
        """
        Extract model references from content.
        
        Args:
            content: Content to extract model references from
            
        Returns:
            Set of model references
        """
        model_refs = set()
        
        # Look for model paths in various formats
        patterns = [
            r'models/([^\s"\']+)\.mdl',  # Direct MDL references
            r'Model\(["\'](.*?)["\']\)',  # Model() function calls
            r'SetModel\(["\'](.*?)["\']\)',  # SetModel() function calls
            r'["\'](models/.*?\.mdl)["\']',  # Quoted model paths
            r'SWEP\.ViewModel\s*=\s*["\'](.*?)["\']',  # SWEP.ViewModel assignments
            r'SWEP\.WorldModel\s*=\s*["\'](.*?)["\']',  # SWEP.WorldModel assignments
            r'self\.ViewModel\s*=\s*["\'](.*?)["\']',  # self.ViewModel assignments
            r'self\.WorldModel\s*=\s*["\'](.*?)["\']'  # self.WorldModel assignments
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                path = match.group(1).strip() if len(match.groups()) > 0 else ""
                if path:
                    # Normalize path format
                    if not path.startswith('models/'):
                        path = f"models/{path}"
                    
                    # Clean up path
                    path = path.replace('\\', '/')
                    
                    # Ensure .mdl extension if it doesn't have one and doesn't have another valid extension
                    valid_extensions = ['.mdl', '.phy', '.vtx', '.vvd']
                    has_valid_extension = any(path.lower().endswith(ext) for ext in valid_extensions)
                    
                    if not has_valid_extension:
                        path = f"{path}.mdl"
                    
                    # Add to model references
                    model_refs.add(path)
        
        return model_refs
    
    def extract_from_swep_table(self, table_content: str) -> Set[str]:
        """
        Extract model references from a SWEP table.
        
        Args:
            table_content: SWEP table content
            
        Returns:
            Set of model references
        """
        model_refs = set()
        
        # Look for model properties
        model_keys = ['ViewModel', 'WorldModel', 'Model']
        
        # String pattern for properties like ViewModel = "models/weapons/v_pistol.mdl"
        string_pattern = r'([A-Za-z0-9_]+)\s*=\s*["\']([^"\']*)["\']'
        for match in re.finditer(string_pattern, table_content, re.DOTALL):
            key = match.group(1).strip()
            value = match.group(2).strip()
            
            if key in model_keys or any(model_key.lower() in key.lower() for model_key in model_keys):
                if value:
                    # Normalize path format
                    if not value.startswith('models/'):
                        value = f"models/{path}"
                    
                    # Clean up path
                    value = value.replace('\\', '/')
                    
                    # Ensure .mdl extension if it doesn't have one and doesn't have another valid extension
                    valid_extensions = ['.mdl', '.phy', '.vtx', '.vvd']
                    has_valid_extension = any(value.lower().endswith(ext) for ext in valid_extensions)
                    
                    if not has_valid_extension:
                        value = f"{value}.mdl"
                    
                    # Add to model references
                    model_refs.add(value)
        
        # Look for function calls like SetModel("models/weapons/v_pistol.mdl")
        func_pattern = r'(?:self\.)?([A-Za-z0-9_]+)\s*\(\s*["\'](.*?)["\']'
        for match in re.finditer(func_pattern, table_content, re.DOTALL):
            func_name = match.group(1).strip().lower()
            value = match.group(2).strip()
            
            if func_name in ['setmodel'] and value:
                # Normalize path format
                if not value.startswith('models/'):
                    value = f"models/{value}"
                
                # Clean up path
                value = value.replace('\\', '/')
                
                # Ensure .mdl extension if it doesn't have one and doesn't have another valid extension
                valid_extensions = ['.mdl', '.phy', '.vtx', '.vvd']
                has_valid_extension = any(value.lower().endswith(ext) for ext in valid_extensions)
                
                if not has_valid_extension:
                    value = f"{value}.mdl"
                
                # Add to model references
                model_refs.add(value)
        
        return model_refs
