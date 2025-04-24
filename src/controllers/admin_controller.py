"""
Admin Controller for Texture Extractor
Handles checking and requesting administrative privileges
"""

import os
import sys
import logging
import ctypes
import subprocess
from pathlib import Path

def check_admin():
    """Check if the script has administrator privileges."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
        return False

def request_admin():
    """Show a message box requesting admin privileges."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        result = messagebox.askyesno(
            "Administrator Privileges Required",
            "This script needs administrator privileges to modify files in the Garry's Mod directory.\n\n" +
            "Would you like to restart the script with administrator privileges?",
            icon='warning'
        )
        
        root.destroy()
        return result
    except Exception as e:
        logging.error(f"Error showing admin request dialog: {e}")
        # If tkinter fails, fall back to console input
        print("\nAdministrator privileges are required.")
        response = input("Would you like to restart with administrator privileges? (y/n): ").lower()
        return response.startswith('y')

def elevate_script():
    """Restart the script with admin privileges."""
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return True
            
        # Get absolute path to the script
        script_path = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script_path)
        
        if getattr(sys, 'frozen', False):
            # If we're running as a compiled executable
            args = [script_path] + sys.argv[1:]
        else:
            # If we're running as a Python script
            args = [sys.executable, script_path] + sys.argv[1:]
        
        # Create a command that will:
        # 1. Change to the correct directory
        # 2. Run the script
        # 3. Keep the window open
        cmd_args = ' '.join(f'"{arg}"' for arg in args)
        cmd = f'cd /d "{script_dir}" && {cmd_args}'
        
        # Use ShellExecuteW for UAC elevation
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            f"/K {cmd}",
            script_dir,  # Set working directory
            1  # SW_SHOWNORMAL
        )
        
        if result <= 32:  # Error codes are <= 32
            raise Exception(f"Failed to elevate privileges. Error code: {result}")
            
        sys.exit(0)  # Exit current instance
        
    except Exception as e:
        logging.error(f"Failed to elevate privileges: {e}")
        return False
