"""
Dependency Controller for Texture Extractor
Handles checking and installing required dependencies
"""

import sys
import logging
import subprocess
from src.config.config_manager import load_config

# Built-in packages that don't need to be installed
BUILT_IN_PACKAGES = [
    'shutil',     # For file operations
    'struct',     # For binary data
    'mmap',       # For memory mapping
    'winreg',     # For registry access
]

# Special packages that need different import names than their pip install names
SPECIAL_PACKAGES = {
    'pywin32': ['win32security', 'win32api', 'win32con', 'win32com'],
    'pillow': ['PIL'],
    'psutil': ['psutil'],
    'vpk': ['vpk'],
}

def read_requirements():
    """Read requirements from requirements.txt file."""
    requirements = []
    try:
        # Get the path to requirements.txt relative to this file
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        req_path = os.path.join(base_dir, 'requirements.txt')
        
        if os.path.exists(req_path):
            logging.info(f"Reading requirements from {req_path}")
            with open(req_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        # Remove version specifiers
                        package = line.split('>=')[0].split('==')[0].split('<')[0].strip()
                        if package:
                            requirements.append(package)
            logging.info(f"Found requirements: {requirements}")
        else:
            logging.warning(f"Requirements file not found at {req_path}")
    except Exception as e:
        logging.error(f"Error reading requirements.txt: {e}")
    
    return requirements

def check_and_install_dependencies():
    """Check and install required packages."""
    config = load_config()
    if config.get("SKIP_DEPENDENCIES", False):
        print("\n[i] Skipping dependency checks as SKIP_DEPENDENCIES is True")
        return True
    
    # Read requirements from requirements.txt
    required_pip_packages = read_requirements()
    
    print("\n=== Checking Dependencies ===")
    print(f"Found {len(required_pip_packages)} packages in requirements.txt")
    
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
    critical_packages = ['pywin32', 'vpk', 'psutil']

    # First check built-in packages
    print("\nChecking built-in packages...")
    for import_name in BUILT_IN_PACKAGES:
        if check_package(import_name):
            print(f"  [+] {import_name} (built-in)")
        else:
            print(f"  [-] {import_name} (built-in) not found - this is unusual")
    
    # Then check packages from requirements.txt
    print("\nChecking packages from requirements.txt...")
    for pip_package in required_pip_packages:
        # Handle special packages with different import names
        if pip_package.lower() in SPECIAL_PACKAGES:
            import_names = SPECIAL_PACKAGES[pip_package.lower()]
            all_imports_ok = True
            
            for import_name in import_names:
                if not check_package(import_name):
                    all_imports_ok = False
                    break
            
            if all_imports_ok:
                print(f"  [+] {pip_package} already installed")
                installed_packages.append(pip_package)
            else:
                print(f"  [-] {pip_package} not found or incomplete")
                missing_packages.append((import_names[0], pip_package))
        else:
            # Regular package where import name matches pip name
            if check_package(pip_package):
                print(f"  [+] {pip_package} already installed")
                installed_packages.append(pip_package)
            else:
                print(f"  [-] {pip_package} not found")
                missing_packages.append((pip_package, pip_package))

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
