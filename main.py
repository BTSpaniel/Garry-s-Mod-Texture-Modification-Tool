#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Source Engine Asset Manager
Main entry point for the application
"""

import sys
import logging
from src.utils.logging_utils import setup_logging
from src.config.config_manager import load_config
from src.gui.main_window import TextureExtractorGUI
from src.controllers.admin_controller import check_admin, request_admin, elevate_script
from src.controllers.dependency_controller import check_and_install_dependencies

VERSION = "1.2.3"
APP_NAME = "Source Engine Asset Manager"

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
    
    # Check dependencies
    if not config.get("SKIP_DEPENDENCIES", False):
        if not check_and_install_dependencies():
            logging.error("Failed to install required dependencies")
            sys.exit(1)
    
    # Start GUI if available
    try:
        app = TextureExtractorGUI()
        app.run()
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
