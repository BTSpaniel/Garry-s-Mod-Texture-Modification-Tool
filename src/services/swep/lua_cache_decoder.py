"""
LuaCacheDecoder Module for Source Engine Asset Manager

This module handles .lc (Lua cache) files. If a SWEP's source .lua file is missing,
it attempts to decode the .lc file to recover the SWEP table and related texture data.
"""

import os
import re
import subprocess
import logging
import base64
import zlib
import lzma
import time
import threading
import traceback
import tempfile
from pathlib import Path
from typing import Dict, Optional, List, Set

# Debug flag to enable detailed tracing
DEBUG_TRACE = True

def debug_print(msg):
    """Print debug message with timestamp and thread ID"""
    if DEBUG_TRACE:
        thread_id = threading.get_ident()
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"[{timestamp}][Thread-{thread_id}][LuaDecoder] {msg}")

class LuaCacheDecoder:
    """Handles decoding of Lua cache files to extract SWEP information."""
    
    def __init__(self, config: Dict = None):
        """
        Initialize the LuaCacheDecoder.
        
        Args:
            config: Configuration dictionary with decoder settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Default paths for luadec or other decompilers
        self.luadec_path = self.config.get('luadec_path', 'tools/luadec/luadec.exe')
        self.temp_dir = tempfile.gettempdir()
        
        # Patterns to identify SWEP tables in decompiled code
        self.swep_patterns = [
            r'SWEP\.ViewModel\s*=\s*["\']([^"\']+)["\']',
            r'SWEP\.WorldModel\s*=\s*["\']([^"\']+)["\']',
            r'self\.ViewModel\s*=\s*["\']([^"\']+)["\']',
            r'self\.WorldModel\s*=\s*["\']([^"\']+)["\']',
            r'\.SetModel\(\s*["\']([^"\']+)["\']',
            r'models/weapons/[^"\']+',
            r'materials/models/weapons/[^"\']+',
        ]
        
    def decode_lc_file(self, lc_file_path: Path) -> str:
        """Attempt to decode a Lua cache file using multiple methods.
        
        Args:
            lc_file_path: Path to the .lc file
            
        Returns:
            Decoded content as string, or empty string if decoding failed
        """
        debug_print(f"Starting decode of {lc_file_path}")
        start_time = time.time()
        
        # First try using luadec if available
        if self._is_luadec_available():
            debug_print(f"Attempting luadec decode for {lc_file_path}")
            try:
                result = self._decode_with_luadec(lc_file_path)
                debug_print(f"luadec decode successful for {lc_file_path}, took {time.time() - start_time:.2f}s")
                return result
            except Exception as e:
                debug_print(f"Failed to decode with luadec: {str(e)}")
                logging.debug(f"Failed to decode with luadec: {e}")
        
        # If luadec fails or isn't available, try binary parsing
        debug_print(f"Attempting binary parsing for {lc_file_path}")
        binary_start = time.time()
        try:
            result = self._decode_binary_lc(lc_file_path)
            debug_print(f"Binary parsing successful for {lc_file_path}, took {time.time() - binary_start:.2f}s")
            return result
        except Exception as e:
            debug_print(f"Failed to decode binary .lc: {str(e)}")
            logging.debug(f"Failed to decode binary .lc: {e}")
            
        # If all else fails, try to extract readable strings
        debug_print(f"Attempting string extraction for {lc_file_path}")
        strings_start = time.time()
        try:
            result = self._extract_readable_strings(lc_file_path)
            debug_print(f"String extraction successful for {lc_file_path}, took {time.time() - strings_start:.2f}s")
            return result
        except Exception as e:
            debug_print(f"Failed to extract readable strings: {str(e)}")
            logging.debug(f"Failed to extract readable strings: {e}")
        
        debug_print(f"All decoding methods failed for {lc_file_path}, total time: {time.time() - start_time:.2f}s")
        return ""
    
    def _is_luadec_available(self) -> bool:
        """Check if luadec is available on the system."""
        debug_print("Checking if luadec is available")
        
        if not self.luadec_path:
            debug_print("No luadec path configured")
            return False
            
        try:
            # Check if the luadec executable exists
            if not os.path.exists(self.luadec_path):
                debug_print(f"Luadec not found at {self.luadec_path}")
                return False
                
            # Try to run luadec with version flag
            debug_print(f"Testing luadec at {self.luadec_path}")
            try:
                subprocess.run([self.luadec_path, "-v"], capture_output=True, check=False, timeout=1)
                debug_print("Luadec test successful")
                return True
            except subprocess.SubprocessError as e:
                debug_print(f"Luadec test failed: {str(e)}")
                return False
        except Exception as e:
            debug_print(f"Error checking luadec: {str(e)}")
            return False
    
    def _decode_binary_lc(self, lc_file_path: Path) -> str:
        """Attempt to decode a binary Lua cache file by parsing its structure.
        
        This is a fallback when luadec is not available.
        """
        debug_print(f"ENTER _decode_binary_lc for {lc_file_path}")
        start_time = time.time()
        
        try:
            debug_print(f"Reading binary file: {lc_file_path}")
            with open(lc_file_path, 'rb') as f:
                content = f.read()
            
            file_size = len(content)
            debug_print(f"Read {file_size} bytes from {lc_file_path}")
            
            # Try Garry's Mod LZMA decompression first (based on the provided script)
            debug_print(f"Attempting Garry's Mod LZMA decompression for {lc_file_path}")
            try:
                # Check if it's a Garry's Mod Lua cache file (usually has .lua extension in cache folder)
                if lc_file_path.suffix.lower() == '.lua' or 'cache/lua' in str(lc_file_path).lower():
                    try:
                        # Skip first 4 bytes as per the script
                        if len(content) > 4:
                            debug_print("Skipping first 4 bytes and attempting LZMA decompression")
                            with lzma.LZMADecompressor() as decompressor:
                                decompressed = decompressor.decompress(content[4:])
                                if decompressed and len(decompressed) > 100:  # Reasonable size check
                                    debug_print(f"LZMA decompression successful, got {len(decompressed)} bytes")
                                    result = decompressed.decode('ascii', errors='ignore').rstrip('\x00')
                                    debug_print(f"LZMA decode completed in {time.time() - start_time:.2f}s")
                                    return result
                                else:
                                    debug_print(f"LZMA decompression result too small: {len(decompressed) if decompressed else 0} bytes")
                    except Exception as e:
                        debug_print(f"LZMA decompression failed: {str(e)}")
            except Exception as e:
                debug_print(f"LZMA decompression process failed: {str(e)}")
                logging.debug(f"LZMA decompression failed: {e}")
            
            # Try to find zlib compressed data
            debug_print(f"Searching for zlib compressed data in {lc_file_path}")
            try:
                # Look for zlib header bytes
                zlib_start = content.find(b'x\x9C')
                if zlib_start >= 0:
                    debug_print(f"Found zlib header at position {zlib_start}")
                    # Try to decompress from this position
                    try:
                        debug_print(f"Attempting zlib decompression from position {zlib_start}")
                        decompressed = zlib.decompress(content[zlib_start:])
                        if decompressed and len(decompressed) > 100:  # Reasonable size check
                            debug_print(f"Zlib decompression successful, got {len(decompressed)} bytes")
                            result = decompressed.decode('utf-8', errors='ignore')
                            debug_print(f"Zlib decode completed in {time.time() - start_time:.2f}s")
                            return result
                        else:
                            debug_print(f"Zlib decompression result too small: {len(decompressed) if decompressed else 0} bytes")
                    except Exception as e:
                        debug_print(f"Zlib decompression failed: {str(e)}")
                else:
                    debug_print(f"No zlib header found in {lc_file_path}")
            except Exception as e:
                debug_print(f"Zlib decompression process failed: {str(e)}")
                logging.debug(f"Zlib decompression failed: {e}")
                
            # Try to find base64 encoded data
            debug_print(f"Searching for base64 encoded data in {lc_file_path}")
            try:
                # Convert binary to string and look for base64-like patterns
                debug_print(f"Converting binary to string for base64 search")
                text_content = content.decode('utf-8', errors='ignore')
                
                # Look for base64 patterns (long strings of base64 chars)
                debug_print(f"Applying base64 pattern matching")
                base64_pattern = re.compile(r'[A-Za-z0-9+/=]{50,}')  # At least 50 chars of base64
                matches = base64_pattern.findall(text_content)
                
                debug_print(f"Found {len(matches)} potential base64 matches")
                for i, match in enumerate(matches):
                    if i >= 5:  # Limit to first 5 matches to avoid hanging
                        debug_print(f"Stopping after checking {i} base64 matches to avoid hanging")
                        break
                        
                    try:
                        debug_print(f"Attempting to decode base64 match {i+1}/{len(matches)} (length: {len(match)})")
                        decoded = base64.b64decode(match)
                        if decoded and len(decoded) > 100:  # Reasonable size check
                            debug_print(f"Base64 decoding successful, got {len(decoded)} bytes")
                            result = decoded.decode('utf-8', errors='ignore')
                            debug_print(f"Base64 decode completed in {time.time() - start_time:.2f}s")
                            return result
                        else:
                            debug_print(f"Base64 decoding result too small: {len(decoded) if decoded else 0} bytes")
                    except Exception as e:
                        debug_print(f"Failed to decode base64 match {i+1}: {str(e)}")
                        continue
            except Exception as e:
                debug_print(f"Base64 decoding process failed: {str(e)}")
                logging.debug(f"Base64 decoding failed: {e}")
                
            # If we couldn't find compressed or encoded data, return the raw content
            debug_print(f"No compressed/encoded data found, returning raw content")
            result = content.decode('utf-8', errors='ignore')
            debug_print(f"Binary decode completed in {time.time() - start_time:.2f}s")
            return result
            
        except Exception as e:
            debug_print(f"CRITICAL ERROR in _decode_binary_lc: {str(e)}")
            traceback.print_exc()
            raise
    
    def _decode_with_luadec(self, lc_file_path: Path) -> str:
        """
        Use luadec to decompile the Lua bytecode.
        
        Args:
            lc_file_path: Path to the .lc file
            
        Returns:
            Decompiled Lua code if successful, empty string otherwise
        """
        debug_print(f"ENTER _decode_with_luadec for {lc_file_path}")
        start_time = time.time()
        
        try:
            # Check if luadec exists
            if not os.path.exists(self.luadec_path):
                debug_print(f"Luadec not found at {self.luadec_path}")
                return ""
                
            # Run luadec on the .lc file directly without output file
            debug_print(f"Running luadec: {self.luadec_path} {lc_file_path}")
            result = subprocess.run(
                [self.luadec_path, str(lc_file_path)],
                capture_output=True,
                text=True,
                timeout=3  # 3 second timeout (reduced from 5)
            )
            
            if result.returncode == 0 and result.stdout:
                debug_print(f"luadec successful, got {len(result.stdout)} bytes")
                debug_print(f"luadec completed in {time.time() - start_time:.2f}s")
                return result.stdout
            else:
                debug_print(f"luadec failed with return code {result.returncode}")
                if result.stderr:
                    debug_print(f"luadec error: {result.stderr[:200]}...")
                return ""
                
        except subprocess.TimeoutExpired:
            debug_print(f"luadec timed out after 3 seconds")
            logging.warning(f"luadec timed out on {lc_file_path}")
            return ""
        except Exception as e:
            debug_print(f"luadec failed with exception: {str(e)}")
            logging.debug(f"luadec failed: {e}")
            return ""
            
    def _extract_readable_strings(self, lc_file_path: Path) -> str:
        """Extract readable strings from a binary file as a last resort."""
        debug_print(f"ENTER _extract_readable_strings for {lc_file_path}")
        start_time = time.time()
        
        try:
            debug_print(f"Reading file for string extraction: {lc_file_path}")
            with open(lc_file_path, 'rb') as f:
                content = f.read()
                
            file_size = len(content)
            debug_print(f"Read {file_size} bytes for string extraction")
            
            # Convert to string, ignoring non-utf8 bytes
            debug_print("Converting binary to string for pattern matching")
            text = content.decode('utf-8', errors='ignore')
            
            # Extract strings that look like they might be Lua code or SWEP references
            debug_print("Setting up Lua pattern matching")
            lua_patterns = [
                r'SWEP\.[\w_]+\s*=',  # SWEP property assignments
                r'function\s+[\w_:]+\s*\(',  # Function definitions
                r'local\s+[\w_]+\s*=',  # Local variable assignments
                r'AddCSLuaFile\(',  # Common Lua function calls
                r'include\(',
                r'resource\.AddFile',
                r'\"models\/.*\.mdl\"',  # Model references
                r'\'materials\/.*\.[\w]+\'',  # Material references
            ]
            
            # Combine patterns and find all matches
            debug_print("Performing pattern matching for Lua code fragments")
            combined_pattern = '|'.join(f'({p})' for p in lua_patterns)
            
            # Limit the number of matches to avoid regex catastrophic backtracking
            debug_print("Executing regex with match limit")
            match_start = time.time()
            
            # Use a safer approach with a timeout mechanism
            max_search_time = 2.0  # seconds
            matches = []
            
            try:
                matches = re.findall(combined_pattern, text[:100000])  # Limit initial search to first 100K chars
                if time.time() - match_start > max_search_time:
                    debug_print(f"Regex taking too long, stopping after {time.time() - match_start:.2f}s")
            except Exception as e:
                debug_print(f"Regex matching failed: {str(e)}")
            
            debug_print(f"Found {len(matches)} pattern matches in {time.time() - match_start:.2f}s")
            
            # Flatten the matches (re.findall with groups returns tuples)
            flattened = [match for group in matches for match in group if match]
            
            # Return the joined matches if we found any
            if flattened:
                debug_print(f"Returning {len(flattened)} string matches")
                result = '\n'.join(flattened)
                debug_print(f"String extraction completed in {time.time() - start_time:.2f}s")
                return result
            
            debug_print("No string matches found")
            return ""
            
        except Exception as e:
            debug_print(f"CRITICAL ERROR in _extract_readable_strings: {str(e)}")
            traceback.print_exc()
            return ""
    
    def _extract_strings_from_binary(self, binary_data: bytes) -> str:
        """
        Extract readable strings from binary data.
        
        Args:
            binary_data: Binary data to extract strings from
            
        Returns:
            Concatenated string of all readable text found
        """
        # Convert to text, ignoring decoding errors
        try:
            text = binary_data.decode('utf-8', errors='ignore')
            return text
        except Exception:
            # Fallback to regex-based extraction
            string_pattern = re.compile(b'[\x20-\x7E]{4,}')  # Printable ASCII characters
            strings = string_pattern.findall(binary_data)
            return '\n'.join(s.decode('utf-8', errors='ignore') for s in strings)
    
    def decode_file(self, file_path: Path) -> str:
        """
        Decode a file (workshop GMA file or Lua cache file).
        
        Args:
            file_path: Path to the file to decode
            
        Returns:
            Decoded content as string, or empty string if decoding failed
        """
        # Check if this is a Lua cache file
        if str(file_path).endswith('.lua.cache') or str(file_path).endswith('.lc'):
            return self.decode_lc_file(file_path)
        
        # For workshop GMA files, just extract readable strings
        if str(file_path).endswith('.gma'):
            try:
                debug_print(f"Extracting readable strings from GMA file: {file_path}")
                with open(file_path, 'rb') as f:
                    binary_data = f.read()
                return self._extract_strings_from_binary(binary_data)
            except Exception as e:
                debug_print(f"Failed to extract strings from GMA file: {e}")
                return ""
        
        # For regular files, just read them
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            debug_print(f"Failed to read file: {e}")
            return ""
    
    def extract_swep_info(self, decoded_content: str) -> Dict:
        """
        Extract SWEP information from decoded Lua content.
        
        Args:
            decoded_content: Decoded Lua code
            
        Returns:
            Dictionary containing extracted SWEP information
        """
        if not decoded_content:
            return {}
            
        swep_info = {
            'view_model': None,
            'world_model': None,
            'materials': [],
            'textures': []
        }
        
        # Extract view model
        view_model_match = re.search(r'SWEP\.ViewModel\s*=\s*["\']([^"\']+)["\']', decoded_content)
        if view_model_match:
            swep_info['view_model'] = view_model_match.group(1)
        
        # Extract world model
        world_model_match = re.search(r'SWEP\.WorldModel\s*=\s*["\']([^"\']+)["\']', decoded_content)
        if world_model_match:
            swep_info['world_model'] = world_model_match.group(1)
        
        # Extract material references
        material_matches = re.finditer(r'materials/([^"\']+\.(vmt|vtf))', decoded_content)
        for match in material_matches:
            material_path = match.group(1)
            if material_path not in swep_info['materials']:
                swep_info['materials'].append(material_path)
        
        # Extract model references that might have associated textures
        model_matches = re.finditer(r'models/([^"\']+\.mdl)', decoded_content)
        for match in model_matches:
            model_path = match.group(1)
            # Models often have associated materials with the same name
            potential_material = f"models/{model_path.replace('.mdl', '')}"
            if potential_material not in swep_info['textures']:
                swep_info['textures'].append(potential_material)
        
        return swep_info
