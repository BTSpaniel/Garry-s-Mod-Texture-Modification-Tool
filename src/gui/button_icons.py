"""
Button icons for the Source Engine Asset Manager GUI
"""
import tkinter as tk
from tkinter import ttk
import base64

# Base64 encoded icons for buttons
PLAY_ICON = """
R0lGODlhEAAQAIABAAAAAP///yH5BAEKAAEALAAAAAAQABAAAAIjjI+py+0Po5y02ouz3rz7D4biSJbmiabqyrbuC8fyTNcFADs=
"""

STOP_ICON = """
R0lGODlhEAAQAIABAAAAAP///yH5BAEKAAEALAAAAAAQABAAAAIYjI+py+0Po5y02ouz3rz7D4biSJbmiaYFADs=
"""

SETTINGS_ICON = """
R0lGODlhEAAQAIABAAAAAP///yH5BAEKAAEALAAAAAAQABAAAAIfjI+py+0PF4i02ouz3rz7D4biSJbmiabqyrbuC8fvAQA7
"""

def create_button_with_icon(parent, text, command, icon_data, **kwargs):
    """Create a button with an icon and text"""
    # Create a frame to hold the button
    frame = ttk.Frame(parent)
    
    # Create the button with padding on the left for icon space
    button = ttk.Button(frame, text="   " + text, command=command, **kwargs)
    button.pack(side="right", fill="both", expand=True)
    
    # We'll skip the icon for now to avoid initialization issues
    # Just return the button and frame
    return button, frame
