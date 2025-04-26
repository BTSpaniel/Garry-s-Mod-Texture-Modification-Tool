"""
Debug script to run the application with error logging.
"""

import sys
import traceback

try:
    # Import the main module
    from main import main
    
    # Run the application
    main()
    
except Exception as e:
    # Print the error
    print(f"Error: {e}")
    print("\nDetailed traceback:")
    traceback.print_exc()
    
    # Keep the console open
    input("\nPress Enter to exit...")
