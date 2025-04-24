"""
Dependency Controller for Texture Extractor
Handles checking and installing required dependencies
"""

import sys
import logging
import subprocess
from src.config.config_manager import load_config

# List of required packages with their pip install names
REQUIRED_PACKAGES = [
    ('vpk', 'vpk'),  # For VPK file handling
    ('shutil', None),         # Built-in, for file operations
    ('pathlib', 'pathlib'),   # For path handling
    ('struct', None),         # Built-in, for binary data
    ('mmap', None),           # Built-in, for memory mapping
    ('winreg', None),         # Built-in, for registry access
    ('win32security', 'pywin32'),  # For Windows security and admin features
    ('win32api', 'pywin32'),      # For Windows API access
    ('win32con', 'pywin32'),      # For Windows constants
    ('win32com', 'pywin32')       # For COM interface
]

def check_and_install_dependencies():
    """Check and install required packages."""
    config = load_config()
    if config.get("SKIP_DEPENDENCIES", False):
        print("\n[i] Skipping dependency checks as SKIP_DEPENDENCIES is True")
        return True
        
    print("\n=== Checking Dependencies ===")
    
    def check_package(package_name):
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False

    def install_package(package_name):
        print(f"  > Installing {package_name}...")
        try:
            # First try with pip
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package_name],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
            
            # Special handling for pywin32
            if package_name == 'pywin32':
                try:
                    # Run post-install script
                    import os
                    python_home = os.path.dirname(sys.executable)
                    scripts_dir = os.path.join(python_home, 'Scripts')
                    post_install_script = os.path.join(scripts_dir, 'pywin32_postinstall.py')
                    if os.path.exists(post_install_script):
                        print("  > Running pywin32 post-install script...")
                        subprocess.check_call([sys.executable, post_install_script, "-install"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                except Exception as e:
                    print(f"  > Warning: pywin32 post-install script failed: {e}")
                    
            return True
        except Exception as pip_error:
            print(f"  > Pip install failed: {pip_error}")
            try:
                # If pip fails, try with easy_install
                subprocess.check_call([sys.executable, "-m", "easy_install", package_name],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                return True
            except Exception as easy_install_error:
                print(f"  > Easy_install failed: {easy_install_error}")
                return False

    missing_packages = []
    installed_packages = []
    critical_packages = ['pywin32', 'vpk']

    # First check what needs to be installed
    print("\nChecking installed packages...")
    for import_name, pip_name in REQUIRED_PACKAGES:
        if pip_name is None:  # Skip built-in packages
            print(f"  [+] {import_name} (built-in)")
            continue
            
        if check_package(import_name):
            print(f"  [+] {import_name} already installed")
            installed_packages.append(import_name)
        else:
            print(f"  [-] {import_name} not found")
            missing_packages.append((import_name, pip_name))

    # If anything needs installing, try to install it
    if missing_packages:
        print("\nAttempting to install missing packages...")
        for import_name, pip_name in missing_packages:
            if install_package(pip_name):
                print(f"  [+] Successfully installed {import_name}")
                installed_packages.append(import_name)
                
                # For pywin32, try to import again after installation
                if pip_name == 'pywin32':
                    try:
                        import win32security
                        print("  [+] Successfully imported win32security after installation")
                    except ImportError as e:
                        print(f"  [!] Failed to import win32security after installation: {e}")
                        return False
            else:
                print(f"  [!] Could not install {import_name}")
                if pip_name in critical_packages:
                    print(f"  [!] {pip_name} is required for core functionality")
                    print(f"  [!] Please install {pip_name} manually using:")
                    print(f"      pip install {pip_name}")
                    return False

    print("\n[+] Dependency check completed")
    return True

def initialize_windows_imports():
    """Initialize Windows-specific imports after dependencies are installed."""
    try:
        import win32security
        import win32api
        import win32con
        from win32com.shell import shell, shellcon
        import ntsecuritycon as con
        return True
    except ImportError as e:
        logging.error(f"Failed to import Windows modules: {e}")
        return False
