#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Source Engine Asset Manager
Main entry point for the application
"""

import sys
import logging
import tkinter as tk
from tkinter import messagebox
import threading
from src.utils.logging_utils import setup_logging
from src.config.config_manager import load_config
from src.gui.main_window import TextureExtractorGUI
from src.controllers.admin_controller import check_admin, request_admin, elevate_script
from src.controllers.dependency_controller import check_and_install_dependencies
from src.services.update_service import UpdateService

VERSION = "1.3.6"
APP_NAME = "Source Engine Asset Manager"

def check_for_updates(config):
    """Check for updates and apply if available."""
    try:
        # Initialize update service
        update_service = UpdateService(config)
        
        # Check for updates in a background thread
        def update_thread():
            update_available, latest_version, release_notes = update_service.check_for_updates()
            
            if update_available:
                # Ask user if they want to update
                root = tk.Tk()
                root.withdraw()  # Hide the root window
                
                message = f"A new version ({latest_version}) is available!\n\nRelease Notes:\n{release_notes[:300]}..."
                if release_notes and len(release_notes) > 300:
                    message += "\n\n(See full release notes on GitHub)"
                    
                message += "\n\nDo you want to update now?"
                
                update_now = messagebox.askyesno("Update Available", message)
                root.destroy()
                
                if update_now:
                    logging.info(f"User chose to update to version {latest_version}")
                    
                    # Download and apply update
                    if update_service.download_update(latest_version):
                        if update_service.apply_update(latest_version):
                            # Show success message
                            root = tk.Tk()
                            root.withdraw()
                            messagebox.showinfo("Update Complete", 
                                              f"Update to version {latest_version} completed successfully.\n\nThe application will now restart.")
                            root.destroy()
                            
                            # Restart application
                            update_service.restart_application()
                        else:
                            # Show error message
                            root = tk.Tk()
                            root.withdraw()
                            messagebox.showerror("Update Failed", 
                                               "Failed to apply update. Please try again later or update manually.")
                            root.destroy()
                    else:
                        # Show error message
                        root = tk.Tk()
                        root.withdraw()
                        messagebox.showerror("Update Failed", 
                                           "Failed to download update. Please check your internet connection and try again.")
                        root.destroy()
        
        # Start update check in background
        update_thread = threading.Thread(target=update_thread)
        update_thread.daemon = True
        update_thread.start()
        
    except Exception as e:
        logging.error(f"Error checking for updates: {e}")

def main():
    """Main entry point for the application."""
    # Setup logging
    setup_logging()
    logging.info(f"{APP_NAME} v{VERSION} starting up...")
    
    # Check for admin privileges
    if not check_admin():
        logging.warning("Running without administrator privileges")
        if request_admin():
            logging.info("Restarting with administrator privileges")
            elevate_script()
            return
        else:
            logging.warning("Continuing without administrator privileges")
    
    # Load configuration
    config = load_config()
    
    # Add version to config
    config["VERSION"] = VERSION
    
    # Check dependencies
    if not config.get("SKIP_DEPENDENCIES", False):
        if not check_and_install_dependencies():
            logging.error("Failed to install required dependencies")
            sys.exit(1)
            
    # Check for updates
    if not config.get("SKIP_UPDATE_CHECK", False):
        # Make sure VERSION is in config
        if "VERSION" not in config:
            config["VERSION"] = VERSION
        check_for_updates(config)
    
    # Start GUI if available
    try:
        app = TextureExtractorGUI()
        app.run()
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
