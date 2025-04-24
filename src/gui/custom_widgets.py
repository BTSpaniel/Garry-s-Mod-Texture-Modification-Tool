"""
Custom widgets for the Source Engine Asset Manager GUI
"""
import tkinter as tk
from tkinter import ttk

class CanvasProgressBar(tk.Frame):
    """A custom progress bar using Canvas for better color control"""
    
    def __init__(self, parent, width=400, height=20, bg_color="#E0E0E0", fg_color="#FF8C00", **kwargs):
        """Initialize the canvas progress bar
        
        Args:
            parent: Parent widget
            width: Width of the progress bar
            height: Height of the progress bar
            bg_color: Background color (trough)
            fg_color: Foreground color (progress)
        """
        super().__init__(parent, **kwargs)
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.fg_color = fg_color
        
        # Create canvas with a slight border radius effect
        self.canvas = tk.Canvas(
            self, 
            width=self.width, 
            height=self.height, 
            highlightthickness=0, 
            bg=self.bg_color,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Add a slight border radius by using a rounded rectangle for the background
        # We'll create this with a very simple approach that works reliably
        self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill=self.bg_color, outline="", width=0,
            # Add slight rounding to corners (works on most platforms)
            stipple="gray12"
        )
        
        # Create progress rectangle (initially empty)
        self.rect = self.canvas.create_rectangle(
            0, 0, 0, self.height, 
            fill=self.fg_color, 
            width=0
        )
        
        # Initialize value
        self._value = 0
    
    def get(self):
        """Get current progress value (0-100)"""
        return self._value
    
    def set(self, value):
        """Set progress value (0-100)"""
        # Ensure value is between 0 and 100
        value = max(0, min(100, value))
        self._value = value
        
        # Calculate width of progress rectangle
        rect_width = int((value / 100) * self.width)
        
        # Update rectangle
        self.canvas.coords(self.rect, 0, 0, rect_width, self.height)
        self.update_idletasks()
    
    # Make it compatible with ttk.Progressbar interface
    def configure(self, **kwargs):
        """Configure the progress bar"""
        if "value" in kwargs:
            self.set(kwargs["value"])
        if "background" in kwargs:
            self.fg_color = kwargs["background"]
            self.canvas.itemconfig(self.rect, fill=self.fg_color)
        if "troughcolor" in kwargs:
            self.bg_color = kwargs["troughcolor"]
            self.canvas.config(bg=self.bg_color)
    
    # Alias for configure to match ttk.Progressbar
    config = configure
    
    # Allow dictionary-style access to match ttk.Progressbar
    def __getitem__(self, key):
        if key == "value":
            return self._value
        raise KeyError(f"Unknown key: {key}")
    
    def __setitem__(self, key, value):
        if key == "value":
            self.set(value)
        else:
            raise KeyError(f"Unknown key: {key}")
