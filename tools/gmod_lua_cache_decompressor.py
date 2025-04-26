#!/usr/bin/env python3
"""
GMod Lua Cache Decompressor

This utility decompresses Garry's Mod Lua cache files (.lua files in the cache/lua folder)
using LZMA decompression. It's based on the script provided and integrated into the
Source Engine Asset Manager.

Usage:
    python gmod_lua_cache_decompressor.py <lua cache folder path>
    
Example:
    python gmod_lua_cache_decompressor.py "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod\cache\lua"
"""

import lzma
import sys
import os
import time
from pathlib import Path


def decompress_lua_cache_file(file_path):
    """Decompress a single Lua cache file using LZMA."""
    try:
        with open(file_path, "rb") as compressed:
            # Skip first 4 bytes as per the original script
            compressed.seek(4)
            
            try:
                with lzma.open(compressed) as decompressed:
                    lua = decompressed.read()
                    lua = lua.decode("ascii", "ignore")
                    return lua.rstrip('\x00')  # Remove null byte
            except Exception as e:
                print(f"Error decompressing {file_path}: {str(e)}")
                return None
    except Exception as e:
        print(f"Error opening {file_path}: {str(e)}")
        return None


def batch_decompress_folder(folder_path):
    """Decompress all Lua cache files in the specified folder."""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: Folder {folder} does not exist")
        return False
        
    output_dir = folder / "decompressed"
    if not output_dir.exists():
        os.makedirs(output_dir)
        
    print(f"[*] Beginning decompression of Lua cache files in {folder}")
    start_time = time.time()
    
    success_count = 0
    error_count = 0
    
    for file_path in folder.glob("*.lua"):
        try:
            print(f"Processing {file_path.name}...")
            decompressed_content = decompress_lua_cache_file(file_path)
            
            if decompressed_content:
                output_file = output_dir / file_path.name
                with open(output_file, "w", encoding="utf-8") as out:
                    out.write(decompressed_content)
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}")
            error_count += 1
            
    elapsed_time = time.time() - start_time
    print(f"[*] Decompression complete in {elapsed_time:.2f} seconds")
    print(f"[*] Successfully decompressed {success_count} files")
    print(f"[*] Failed to decompress {error_count} files")
    print(f"[*] Decompressed files saved to {output_dir}")
    
    return True


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: gmod_lua_cache_decompressor.py <lua cache folder path>")
        print("Example: gmod_lua_cache_decompressor.py \"C:\\Program Files (x86)\\Steam\\steamapps\\common\\GarrysMod\\garrysmod\\cache\\lua\"")
        sys.exit(1)
        
    folder_path = sys.argv[1]
    batch_decompress_folder(folder_path)


if __name__ == "__main__":
    main()
