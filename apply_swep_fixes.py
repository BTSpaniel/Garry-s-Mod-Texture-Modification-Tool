"""
Script to apply SWEP detector fixes to the main module.
This script copies the fixed methods from swep_detector_fixes.py to the main swep_detector.py file.
"""
import re
import os
from pathlib import Path

def main():
    print("Applying SWEP detector fixes...")
    
    # Read the fixes file
    fixes_path = Path("swep_detector_fixes.py")
    if not fixes_path.exists():
        print("Error: swep_detector_fixes.py not found!")
        return
    
    with open(fixes_path, 'r', encoding='utf-8') as f:
        fixes_content = f.read()
    
    # Read the main SWEP detector module
    swep_detector_path = Path("src/services/swep/swep_detector.py")
    if not swep_detector_path.exists():
        print(f"Error: {swep_detector_path} not found!")
        return
    
    with open(swep_detector_path, 'r', encoding='utf-8') as f:
        detector_content = f.read()
    
    # Extract method definitions from the fixes file
    method_pattern = r'def (_[a-zA-Z0-9_]+\([^)]*\)):[^\n]*\n\s+"""([^"]*)"""(.*?)(?=\n\ndef |$)'
    methods = re.findall(method_pattern, fixes_content, re.DOTALL)
    
    # Create a backup of the original file
    backup_path = swep_detector_path.with_suffix('.py.bak')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(detector_content)
    print(f"Created backup at {backup_path}")
    
    # Replace or add each method to the detector file
    updated_content = detector_content
    for method_signature, docstring, method_body in methods:
        method_name = method_signature.split('(')[0].strip()
        print(f"Processing method: {method_name}")
        
        # Create the full method text
        full_method = f"def {method_signature}:\n    \"\"\"{docstring}\"\"\"{method_body}"
        
        # Check if the method already exists in the file
        existing_method_pattern = rf'def {method_name}\([^)]*\):[^\n]*\n\s+""".*?""".*?(?=\n\s+def |$)'
        if re.search(existing_method_pattern, updated_content, re.DOTALL):
            # Replace the existing method
            updated_content = re.sub(existing_method_pattern, full_method, updated_content, flags=re.DOTALL)
            print(f"  - Replaced existing method: {method_name}")
        else:
            # Add the method at the end of the class
            class_end_pattern = r'(\n\s+def generate_vmt_files.*?)(return count)'
            if re.search(class_end_pattern, updated_content, re.DOTALL):
                updated_content = re.sub(class_end_pattern, r'\1\2\n\n    ' + full_method, updated_content, flags=re.DOTALL)
                print(f"  - Added new method: {method_name}")
            else:
                print(f"  - Could not find a place to add method: {method_name}")
    
    # Write the updated content back to the file
    with open(swep_detector_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("SWEP detector fixes applied successfully!")
    print("You can now run the standalone SWEP analyzer or use the main application to detect SWEPs.")

if __name__ == "__main__":
    main()
