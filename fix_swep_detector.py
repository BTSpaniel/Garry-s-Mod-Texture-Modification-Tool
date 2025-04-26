"""
Script to fix the indentation error in the SWEP detector module.
"""

def main():
    # Path to the SWEP detector module
    swep_detector_path = "src/services/swep/swep_detector.py"
    backup_path = "src/services/swep/swep_detector.py.bak"
    
    try:
        # Read the original file
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the start and end of the problematic section
        start_marker = "        except Exception as e:\n            logging.debug(f\"Regular Lua processing failed for {lua_file.name}: {e}\")\n"
        end_marker = "    def _parse_swep_table"
        
        # Split the content into parts
        parts = content.split(start_marker)
        if len(parts) != 2:
            print(f"Could not find start marker. Found {len(parts)} parts.")
            return
        
        before_problem = parts[0] + start_marker
        
        parts = parts[1].split(end_marker)
        if len(parts) != 2:
            print(f"Could not find end marker. Found {len(parts)} parts.")
            return
        
        after_problem = end_marker + parts[1]
        
        # Create a fixed middle section
        fixed_middle = "            return set(), set(), {}, False\n\n"
        
        # Combine the parts
        fixed_content = before_problem + fixed_middle + after_problem
        
        # Write the fixed content back to the file
        with open(swep_detector_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("Fixed the indentation error in the SWEP detector module.")
        
    except Exception as e:
        print(f"Error fixing SWEP detector module: {e}")

if __name__ == "__main__":
    main()
