"""
Logging utilities for Source Engine Asset Manager
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from src.config.config_manager import load_config

def setup_logging():
    """Initialize logging configuration."""
    try:
        # Load configuration
        config = load_config()
        logging_config = config.get("LOGGING", {})
        
        # Create logs directory if it doesn't exist
        log_dir = Path(logging_config.get("log_location") or "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up log file name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"source_engine_asset_manager_{timestamp}.log"

        # Custom filter to exclude detailed error messages
        class ErrorFilter(logging.Filter):
            def filter(self, record):
                # Filter out detailed syntax and linter errors
                msg = record.getMessage().lower()
                
                # Technical errors to filter
                technical_errors = [
                    'unexpected indent',
                    'unindent',
                    'indentation',
                    'syntax error',
                    'invalid syntax',
                    'expected expression',
                    'expected an indented block',
                    'inconsistent use of tabs',
                    'no attribute',
                    'attribute error',
                    'name error',
                    'type error',
                    'index error',
                    'key error',
                    'value error',
                    'assertion error',
                    'runtime error'
                ]
                
                # Only show user-friendly errors
                if record.levelno >= logging.ERROR:
                    # Convert technical errors to user-friendly messages
                    if any(err in msg for err in technical_errors):
                        return False  # Filter out technical errors
                    
                    # Keep user-friendly error messages
                    user_friendly = any(x in msg for x in [
                        'permission denied',
                        'access denied',
                        'file not found',
                        'directory not found',
                        'failed to create',
                        'could not open',
                        'error processing',
                        'error creating'
                    ])
                    return user_friendly
                    
                # For non-error messages, show progress and success messages
                return not any(err in msg for err in technical_errors)
        
        # Configure logging format based on settings
        log_format = logging_config.get("log_format", "detailed")
        if log_format == "detailed":
            format_str = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        elif log_format == "debug":
            format_str = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        else:  # basic
            format_str = '%(message)s'
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, logging_config.get("log_level", "INFO")))
        
        # Clear any existing handlers
        root_logger.handlers = []
        
        # Create console handler with custom filter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        console_handler.addFilter(ErrorFilter())
        root_logger.addHandler(console_handler)
        
        # Create file handler if enabled (keeps detailed logs)
        if logging_config.get("log_to_file", True):
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(format_str))
            root_logger.addHandler(file_handler)
        
        # Rotate old log files if needed
        if logging_config.get("log_to_file", True):
            log_files = sorted(log_dir.glob('texture_extractor_*.log'))
            max_log_files = logging_config.get("max_log_files", 5)
            while len(log_files) > max_log_files:
                try:
                    log_files[0].unlink()
                    log_files = log_files[1:]
                except Exception as e:
                    logging.warning(f"Could not remove old log file")
                    break
        
        # Import here to avoid circular imports
        import sys
        import importlib.util
        
        # Dynamically import APP_NAME and VERSION from main module
        try:
            # Get the path to main.py
            main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'main.py')
            spec = importlib.util.spec_from_file_location("main", main_path)
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)
            
            # Get APP_NAME and VERSION from main module
            app_name = getattr(main_module, 'APP_NAME', 'Source Engine Asset Manager')
            version = getattr(main_module, 'VERSION', '1.0.0')
            
            logging.info(f"{app_name} v{version} logging initialized")
        except Exception as e:
            # Fallback if import fails
            logging.info("Source Engine Asset Manager logging initialized")
        
    except Exception as e:
        print("Could not set up logging, using basic console output")
        # Set up basic console logging as fallback
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s'
        )
