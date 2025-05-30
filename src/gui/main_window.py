"""
Main Window for Source Engine Asset Manager GUI
"""

import os
import time
import logging
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config.config_manager import load_config
from src.controllers.filesystem_controller import find_steam_path, find_game_paths, find_vpk_files, open_materials_folder
from src.services.file_processor import FileProcessor
# Import VMTGenerator for VMT file creation
from src.services.swep import VMTGenerator
from src.gui.settings_dialog import SettingsDialog
from src.gui.button_icons import create_button_with_icon, PLAY_ICON, STOP_ICON, SETTINGS_ICON

class TextureExtractorGUI:
    """Main GUI window for Source Engine Asset Manager."""
    
    def __init__(self):
        """Initialize the GUI"""
        logging.info("Initializing GUI...")
        
        # Load configuration
        self.config = load_config()
        self.gui_config = self.config.get("GUI", {})
        
        # Log the module settings from the config
        module_config = self.config.get("MODULES", {})
        logging.info(f"Loaded module settings from config: {module_config}")
        
        # Initialize the main window
        self.window = tk.Tk()
        
        # Import main module to get consistent APP_NAME and VERSION
        import importlib.util
        import os
        
        # Get the path to main.py
        main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'main.py')
        spec = importlib.util.spec_from_file_location("main", main_path)
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        # Get APP_NAME and VERSION from main module
        app_name = getattr(main_module, 'APP_NAME', 'Source Engine Asset Manager')
        version = getattr(main_module, 'VERSION', '1.2.1')
        
        self.app_name = app_name
        self.version = version
        
        self.window.title(f"{app_name} v{version}")
        # Set a fixed window size with significantly increased height
        self.window.geometry("950x950")
        # Make the window non-resizable
        self.window.resizable(False, False)
        logging.info(f"Main window created with title: {app_name} v{version}")
        
        # Set application icon
        try:
            # Get the path to the assets directory relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))  # Go up two levels to reach project root
            icon_path = os.path.join(root_dir, "assets", "icon.png")
            
            if os.path.exists(icon_path):
                # Load the icon
                icon = tk.PhotoImage(file=icon_path)
                # Set as window icon
                self.window.iconphoto(True, icon)
                # Keep a reference to prevent garbage collection
                self.icon = icon
                logging.info(f"Application icon set from {icon_path}")
            else:
                logging.warning(f"Icon file not found at {icon_path}")
        except Exception as e:
            logging.error(f"Error setting application icon: {e}")
        
        # Center the window on screen
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = 950
        window_height = 950
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        logging.info("Window positioned")
        
        # Apply custom styles
        self._apply_custom_styles()
        
        # Configure main window grid
        self.window.grid_columnconfigure(0, weight=1)
        
        # Initialize state variables
        self.is_processing = False
        self.processing_thread = None
        self.files_found = 0
        self.processed_files = 0
        self.total_files = 0
        self.start_time = None
        self.last_gui_update = 0
        
        # Initialize C4 sound replacement counter
        self.c4_sounds_replaced = 0
        self.gui_update_interval = 100
        self.progress_var = tk.DoubleVar()
        self.errors = 0
        self.last_update = time.time()
        self.update_threshold = 0.1  # Update GUI every 100ms
        logging.info("State variables initialized")
        
        # Add cache variables
        self.steam_path = None
        self.game_paths = None
        self.vpk_files = None
        self.preload_complete = False
        self.preload_thread = None
        
        # Add VMT counter and deletion counter to state variables
        self.vmt_files_created = 0
        self.vmt_files_deleted = 0  # New counter for deleted VMTs
        self.c4_sounds_replaced = 0  # Counter for replaced C4 sounds
        
        # Add SWEP detection counters
        self.sweps_detected = 0
        self.lua_files_processed = 0
        self.lua_cache_files_processed = 0
        self.swep_textures_found = 0
        self.swep_models_found = 0
        self.addons_scanned = 0
        self.workshop_items_scanned = 0
        self.current_swep_phase = ""
        
        try:
            # Create main container with increased padding
            self.main_container = ttk.Frame(self.window, padding=40)
            self.main_container.grid(row=0, column=0, sticky="nsew")
            self.main_container.grid_columnconfigure(0, weight=1)
            logging.info("Main container created")
            
            # Setup GUI components
            self._setup_gui()
            logging.info("GUI components set up")
            
            # Make sure window appears on top
            self.window.lift()
            self.window.attributes('-topmost', True)
            self.window.after(1000, lambda: self.window.attributes('-topmost', False))
            
            # Force an update to show the window
            self.window.update()
            logging.info("Window visibility enforced")
            
            # Start preloading
            self.start_preload()
            logging.info("Preload started")
            
            # Start GUI update loop
            self._update_gui()
            logging.info("GUI update loop started")
            
        except Exception as e:
            logging.error(f"Error during GUI initialization: {e}")
            raise
    
    def _apply_custom_styles(self):
        """Apply custom styles to the GUI components"""
        try:
            # Configure ttk styles
            style = ttk.Style()
            
            # Define colors
            primary_color = '#FF9933'  # Orange (from the icon)
            secondary_color = '#333333'  # Dark gray
            bg_color = '#F5F5F5'  # Light gray background
            text_color = '#212121'  # Near black for text
            accent_color = '#4a86e8'  # Blue accent
            
            # Configure fonts
            title_font = ('Segoe UI', 22, 'bold')
            subtitle_font = ('Segoe UI', 10)
            button_font = ('Segoe UI', 10, 'bold')
            label_font = ('Segoe UI', 10)
            heading_font = ('Segoe UI', 11, 'bold')
            
            # Apply colors to window
            self.window.configure(background=bg_color)
            
            # Configure widget styles
            style.configure('TFrame', background=bg_color)
            style.configure('TLabel', background=bg_color, foreground=text_color, font=label_font)
            style.configure('TButton', 
                          font=button_font, 
                          background=bg_color, 
                          foreground=text_color,
                          borderwidth=1,
                          relief='flat')
            style.map('TButton',
                     background=[('active', primary_color), ('pressed', '#D97000')],
                     foreground=[('active', 'white'), ('pressed', 'white')])
            
            # Create custom button styles
            style.configure('Primary.TButton', 
                          font=button_font, 
                          background='#FF8C00', 
                          foreground=text_color,
                          borderwidth=1,
                          relief='flat')
            style.map('Primary.TButton',
                     background=[('active', '#D97000'), ('pressed', '#B86000')],
                     foreground=[('active', text_color), ('pressed', text_color)])
                     
            # Configure labelframe styles
            style.configure('TLabelframe', background=bg_color, foreground=text_color, font=heading_font)
            style.configure('TLabelframe.Label', background=bg_color, foreground=primary_color, font=heading_font)
            
            # Configure notebook styles
            style.configure('TNotebook', background=bg_color, tabmargins=[2, 5, 2, 0])
            style.configure('TNotebook.Tab', background=bg_color, foreground=text_color, font=label_font, padding=[10, 4])
            style.map('TNotebook.Tab', background=[('selected', primary_color)], foreground=[('selected', secondary_color)])
            
            # Configure progress bar with orange color
            style.configure('Horizontal.TProgressbar', 
                          background=primary_color,
                          troughcolor='#E0E0E0',
                          borderwidth=0,
                          thickness=20)
            
            # Custom title style
            style.configure('Title.TLabel', font=title_font, foreground=primary_color, background=bg_color)
            style.configure('Subtitle.TLabel', font=subtitle_font, foreground=secondary_color, background=bg_color)
            
            # Custom header frame style
            style.configure('Header.TFrame', background=bg_color)
            
            # Custom status label style
            style.configure('Status.TLabel', font=label_font, foreground=secondary_color, background=bg_color)
            
            # Custom stat value style
            style.configure('StatValue.TLabel', font=('Segoe UI', 10, 'bold'), foreground=primary_color, background=bg_color)
            
        except Exception as e:
            logging.warning(f"Could not apply custom styles: {e}")
    
    def run(self):
        """Start the GUI main loop"""
        try:
            # Start the GUI main loop
            self.window.mainloop()
        except Exception as e:
            logging.error(f"Error in GUI main loop: {e}")
            raise
        finally:
            logging.info("Cleaning up GUI resources")
            self.is_processing = False
            if self.processing_thread and self.processing_thread.is_alive():
                try:
                    self.processing_thread.join(timeout=1.0)
                except Exception as e:
                    logging.error(f"Error stopping thread during shutdown: {e}")
    
    def start_preload(self):
        """Start preloading data in a separate thread."""
        self.status_label.config(text="Preloading data...")
        self.start_button.config(state="disabled")
        self.preload_thread = threading.Thread(target=self._preload_data)
        self.preload_thread.daemon = True
        self.preload_thread.start()
    
    def _setup_gui(self):
        """Setup GUI components"""
        try:
            # Header with app icon, title and version
            header_frame = ttk.Frame(self.main_container)
            header_frame.grid(row=0, column=0, columnspan=2, pady=(5, 25), sticky="ew")
            
            # Create a horizontal container for icon and title
            title_container = ttk.Frame(header_frame)
            title_container.pack(pady=(0, 5))
            
            # Add icon to the header if available
            if hasattr(self, 'icon'):
                # Create a smaller version for the header
                header_icon = self.icon.subsample(4, 4)  # Reduce size to 1/4
                icon_label = ttk.Label(title_container, image=header_icon)
                icon_label.image = header_icon  # Keep a reference
                icon_label.pack(side="left", padx=(0, 10))
            
            # App title with enhanced styling
            self.title_label = ttk.Label(
                title_container, 
                text="Source Engine Asset Manager",
                style='Title.TLabel'
            )
            self.title_label.pack(side="left")
            
            # Version subtitle
            self.version_label = ttk.Label(
                header_frame, 
                text=f"Version {self.version}",
                style='Subtitle.TLabel'
            )
            self.version_label.pack(pady=(0, 10))

            # Button frame with modern styling and rounded corners
            button_frame = ttk.Frame(self.main_container)
            button_frame.grid(row=1, column=0, columnspan=2, pady=(0, 25), sticky="ew")
            button_frame.grid_columnconfigure(0, weight=1)
            button_frame.grid_columnconfigure(1, weight=1)
            button_frame.grid_columnconfigure(2, weight=1)

            # Buttons with consistent width and modern style
            button_width = 18
            start_button_style = {'width': button_width, 'padding': 8, 'style': 'Primary.TButton'}
            button_style = {'width': button_width, 'padding': 8}
            
            # Start button with play icon and primary style
            self.start_button, start_frame = create_button_with_icon(
                button_frame, 
                "Start Processing", 
                self.start_processing,
                PLAY_ICON,
                **start_button_style
            )
            start_frame.grid(row=0, column=0, padx=15)

            # Stop button with stop icon
            self.stop_button, stop_frame = create_button_with_icon(
                button_frame, 
                "Stop", 
                self.stop_processing,
                STOP_ICON,
                **button_style
            )
            stop_frame.grid(row=0, column=1, padx=15)
            self.stop_button.config(state="disabled")

            # Settings button with gear icon
            self.settings_button, settings_frame = create_button_with_icon(
                button_frame, 
                "Settings", 
                self.show_settings,
                SETTINGS_ICON,
                **button_style
            )
            settings_frame.grid(row=0, column=2, padx=15)

            # Status frame to contain both status and time
            status_frame = ttk.Frame(self.main_container)
            status_frame.grid(row=2, column=0, columnspan=2, pady=(10, 10), sticky="ew")
            status_frame.grid_columnconfigure(0, weight=1)
            
            # Status label with modern styling
            self.status_frame = ttk.Frame(self.main_container, padding=5)
            self.status_frame.grid(row=2, column=0, columnspan=2, pady=(0, 15), sticky="ew")
            self.status_frame.grid_columnconfigure(0, weight=1)
            
            self.status_label = ttk.Label(
                self.status_frame, 
                text="Ready",
                style='Status.TLabel',
                anchor="center"
            )
            self.status_label.grid(row=0, column=0, sticky="ew")

            # Time label
            self.time_label = ttk.Label(
                status_frame,
                text="Time: 0:00:00",
                justify="center"
            )
            self.time_label.grid(row=1, column=0, sticky="ew", pady=(5, 0))

            # Progress frame with modern styling and shadow effect
            progress_frame = ttk.LabelFrame(self.main_container, text="Progress", padding=20)
            progress_frame.grid(row=3, column=0, columnspan=2, pady=(0, 20), sticky="ew", padx=15)
            progress_frame.grid_columnconfigure(0, weight=1)
            
            # Status information row
            status_frame = ttk.Frame(progress_frame)
            status_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            status_frame.grid_columnconfigure(0, weight=1)
            status_frame.grid_columnconfigure(1, weight=1)
            
            # Current phase display
            phase_frame = ttk.Frame(status_frame)
            phase_frame.grid(row=0, column=0, sticky="w")
            ttk.Label(phase_frame, text="Current Phase: ", style='StatLabel.TLabel').pack(side="left")
            self.current_phase_label = ttk.Label(phase_frame, text="None", foreground="#FF8C00")
            self.current_phase_label.pack(side="left")
            
            # Scan task progress display
            self.scan_task_frame = ttk.Frame(status_frame)
            self.scan_task_frame.grid(row=1, column=0, sticky="w", pady=(5, 0))
            self.scan_task_label = ttk.Label(self.scan_task_frame, text="", foreground="#0066CC")
            self.scan_task_label.pack(side="left")
            
            # File count display
            file_count_frame = ttk.Frame(status_frame)
            file_count_frame.grid(row=0, column=1, sticky="e")
            self.file_count_label = ttk.Label(file_count_frame, text="Ready to process 0 files", foreground="#006400")
            self.file_count_label.pack(side="right")
            
            # Overall progress label with improved styling
            ttk.Label(progress_frame, text="Overall Progress:").grid(row=1, column=0, sticky="w", pady=(0, 3))
            
            # Main progress bar (overall progress) with enhanced styling
            self.progress_bar = ttk.Progressbar(
                progress_frame, 
                orient="horizontal", 
                mode="determinate", 
                length=800
            )
            self.progress_bar.grid(row=2, column=0, sticky="ew", pady=(0, 15))
            
            # Current action label with improved styling
            ttk.Label(progress_frame, text="Current Action:").grid(row=3, column=0, sticky="w", pady=(0, 3))
            
            # Action progress bar (current task progress) with enhanced styling
            self.action_progress_bar = ttk.Progressbar(
                progress_frame, 
                orient="horizontal", 
                mode="determinate", 
                length=800
            )
            self.action_progress_bar.grid(row=4, column=0, sticky="ew")
            
            # Add percentage labels next to progress bars
            self.overall_percent_label = ttk.Label(progress_frame, text="0%", style='StatValue.TLabel')
            self.overall_percent_label.grid(row=2, column=1, padx=(5, 0))
            
            self.action_percent_label = ttk.Label(progress_frame, text="0%", style='StatValue.TLabel')
            self.action_percent_label.grid(row=4, column=1, padx=(5, 0))

            # Stats frame with enhanced styling and shadow effect
            self.stats_frame = ttk.LabelFrame(
                self.main_container, 
                text="Statistics", 
                padding="20"
            )
            self.stats_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 20))
            
            # Configure stats frame to maintain minimum width
            self.stats_frame.grid_columnconfigure(0, weight=1)
            self.stats_frame.grid_columnconfigure(1, weight=1)
            
            # Create a notebook for tabbed statistics
            self.stats_notebook = ttk.Notebook(self.stats_frame)
            self.stats_notebook.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
            


            # Create frames for each tab with proper padding
            self.general_stats_frame = ttk.Frame(self.stats_notebook, padding=10)
            self.swep_stats_frame = ttk.Frame(self.stats_notebook, padding=10)
            self.modules_stats_frame = ttk.Frame(self.stats_notebook, padding=10)
            
            # Add tabs to notebook
            self.stats_notebook.add(self.general_stats_frame, text="General")
            self.stats_notebook.add(self.swep_stats_frame, text="SWEP Detection")
            self.stats_notebook.add(self.modules_stats_frame, text="Modules")
            
            # Set a fixed width for the notebook to prevent squeezing
            self.stats_notebook.config(width=780, height=180)
            
            # Configure the frames
            for frame in [self.general_stats_frame, self.swep_stats_frame, self.modules_stats_frame]:
                frame.grid_columnconfigure(0, weight=1)
                frame.grid_columnconfigure(1, weight=1)
                
            # Set up module stats UI
            self._setup_module_stats()

            # Stats labels with consistent formatting
            self.stats_labels = {}
            stats_to_show = [
                ('Files Found:', 'found', '0'),
                ('Files Processed:', 'files', '0'),
                ('VMTs Created:', 'vmts', '0'),
                ('VMTs Deleted:', 'deleted', '0'),  # Add deletion counter
                ('C4 Sounds Replaced:', 'c4_sounds', '0'),  # Add C4 sounds counter
                ('Success Rate:', 'rate', '0%'),
                ('Errors:', 'errors', '0'),
                ('Processing Time:', 'time', '0:00:00')
            ]
            
            for i, (label_text, key, initial_value) in enumerate(stats_to_show):
                row = i // 2
                col = i % 2
                
                # Create a container frame for each stat with better styling
                stat_frame = ttk.Frame(self.general_stats_frame)
                stat_frame.grid(row=row, column=col, sticky="w", padx=10, pady=4)
                
                # Add the label with improved font
                label = ttk.Label(stat_frame, text=label_text, font=('Segoe UI', 9))
                label.pack(side="left")
                
                # Add the value with improved font and styling
                value = ttk.Label(stat_frame, text=initial_value, style='StatValue.TLabel')
                value.pack(side="left", padx=(5, 0))
                
                # Store reference to the value label
                self.stats_labels[key] = value
                
            # SWEP stats labels with improved styling
            swep_label_style = {'sticky': "w", 'pady': 4, 'padx': 10}
            swep_value_style = {'style': 'StatValue.TLabel'}
            
            # Create frames for each SWEP stat for better layout
            # Create general statistics with a simple grid layout
            # Left column
            row = 0
            
            # Create a container frame for each stat to ensure proper spacing
            left_frame1 = ttk.Frame(self.general_stats_frame)
            left_frame1.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
            left_frame1.columnconfigure(0, weight=1)
            left_frame1.columnconfigure(1, weight=1)
            
            ttk.Label(left_frame1, text="Files Found: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.stats_labels['found'] = ttk.Label(left_frame1, text="0", style='StatValue.TLabel')
            self.stats_labels['found'].grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Right column
            right_frame1 = ttk.Frame(self.general_stats_frame)
            right_frame1.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
            right_frame1.columnconfigure(0, weight=1)
            right_frame1.columnconfigure(1, weight=1)
            
            ttk.Label(right_frame1, text="Files Processed: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.stats_labels['processed'] = ttk.Label(right_frame1, text="0", style='StatValue.TLabel')
            self.stats_labels['processed'].grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Row 2
            row = 1
            
            # Create a container frame for each stat to ensure proper spacing
            left_frame2 = ttk.Frame(self.general_stats_frame)
            left_frame2.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
            left_frame2.columnconfigure(0, weight=1)
            left_frame2.columnconfigure(1, weight=1)
            
            ttk.Label(left_frame2, text="VMTs Created: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.stats_labels['created'] = ttk.Label(left_frame2, text="0", style='StatValue.TLabel')
            self.stats_labels['created'].grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Right column
            right_frame2 = ttk.Frame(self.general_stats_frame)
            right_frame2.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
            right_frame2.columnconfigure(0, weight=1)
            right_frame2.columnconfigure(1, weight=1)
            
            ttk.Label(right_frame2, text="VMTs Deleted: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.stats_labels['deleted'] = ttk.Label(right_frame2, text="0", style='StatValue.TLabel')
            self.stats_labels['deleted'].grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Row 3
            row = 2
            
            # Create a container frame for each stat to ensure proper spacing
            left_frame3 = ttk.Frame(self.general_stats_frame)
            left_frame3.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
            left_frame3.columnconfigure(0, weight=1)
            left_frame3.columnconfigure(1, weight=1)
            
            ttk.Label(left_frame3, text="C4 Sounds Replaced: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.stats_labels['sounds'] = ttk.Label(left_frame3, text="0", style='StatValue.TLabel')
            self.stats_labels['sounds'].grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Right column
            right_frame3 = ttk.Frame(self.general_stats_frame)
            right_frame3.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
            right_frame3.columnconfigure(0, weight=1)
            right_frame3.columnconfigure(1, weight=1)
            
            ttk.Label(right_frame3, text="Success Rate: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.stats_labels['rate'] = ttk.Label(right_frame3, text="0%", style='StatValue.TLabel')
            self.stats_labels['rate'].grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Row 4
            row = 3
            
            # Create a container frame for each stat to ensure proper spacing
            left_frame4 = ttk.Frame(self.general_stats_frame)
            left_frame4.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
            left_frame4.columnconfigure(0, weight=1)
            left_frame4.columnconfigure(1, weight=1)
            
            ttk.Label(left_frame4, text="Errors: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.stats_labels['errors'] = ttk.Label(left_frame4, text="0", style='StatValue.TLabel')
            self.stats_labels['errors'].grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Right column
            right_frame4 = ttk.Frame(self.general_stats_frame)
            right_frame4.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
            right_frame4.columnconfigure(0, weight=1)
            right_frame4.columnconfigure(1, weight=1)
            
            ttk.Label(right_frame4, text="Processing Time: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.stats_labels['time'] = ttk.Label(right_frame4, text="00:00:00", style='StatValue.TLabel')
            self.stats_labels['time'].grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Current Phase removed - now displayed in progress bar section

            # SWEPs Detected
            swep_detected_frame = ttk.Frame(self.swep_stats_frame)
            swep_detected_frame.grid(row=0, column=0, sticky="ew", pady=4, padx=10)
            swep_detected_frame.columnconfigure(0, weight=1)
            swep_detected_frame.columnconfigure(1, weight=1)
            ttk.Label(swep_detected_frame, text="SWEPs Detected: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.sweps_detected_label = ttk.Label(swep_detected_frame, text="0", style='StatValue.TLabel')
            self.sweps_detected_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Lua Files
            lua_files_frame = ttk.Frame(self.swep_stats_frame)
            lua_files_frame.grid(row=1, column=0, sticky="ew", pady=4, padx=10)
            lua_files_frame.columnconfigure(0, weight=1)
            lua_files_frame.columnconfigure(1, weight=1)
            ttk.Label(lua_files_frame, text="Lua Files: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.lua_files_label = ttk.Label(lua_files_frame, text="0", style='StatValue.TLabel')
            self.lua_files_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Cache Files
            lua_cache_frame = ttk.Frame(self.swep_stats_frame)
            lua_cache_frame.grid(row=2, column=0, sticky="ew", pady=4, padx=10)
            lua_cache_frame.columnconfigure(0, weight=1)
            lua_cache_frame.columnconfigure(1, weight=1)
            ttk.Label(lua_cache_frame, text="Cache Files: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.lua_cache_label = ttk.Label(lua_cache_frame, text="0", style='StatValue.TLabel')
            self.lua_cache_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Textures Found
            textures_found_frame = ttk.Frame(self.swep_stats_frame)
            textures_found_frame.grid(row=0, column=1, sticky="ew", pady=4, padx=10)
            textures_found_frame.columnconfigure(0, weight=1)
            textures_found_frame.columnconfigure(1, weight=1)
            ttk.Label(textures_found_frame, text="Textures Found: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.swep_textures_label = ttk.Label(textures_found_frame, text="0", style='StatValue.TLabel')
            self.swep_textures_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Models Found
            models_found_frame = ttk.Frame(self.swep_stats_frame)
            models_found_frame.grid(row=1, column=1, sticky="ew", pady=4, padx=10)
            models_found_frame.columnconfigure(0, weight=1)
            models_found_frame.columnconfigure(1, weight=1)
            ttk.Label(models_found_frame, text="Models Found: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.swep_models_label = ttk.Label(models_found_frame, text="0", style='StatValue.TLabel')
            self.swep_models_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Addons Scanned
            addons_scanned_frame = ttk.Frame(self.swep_stats_frame)
            addons_scanned_frame.grid(row=3, column=0, sticky="ew", pady=4, padx=10)
            addons_scanned_frame.columnconfigure(0, weight=1)
            addons_scanned_frame.columnconfigure(1, weight=1)
            ttk.Label(addons_scanned_frame, text="Addons Scanned: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.addons_label = ttk.Label(addons_scanned_frame, text="0", style='StatValue.TLabel')
            self.addons_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Workshop Items
            workshop_items_frame = ttk.Frame(self.swep_stats_frame)
            workshop_items_frame.grid(row=3, column=1, sticky="ew", pady=4, padx=10)
            workshop_items_frame.columnconfigure(0, weight=1)
            workshop_items_frame.columnconfigure(1, weight=1)
            ttk.Label(workshop_items_frame, text="Workshop Items: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.workshop_label = ttk.Label(workshop_items_frame, text="0", style='StatValue.TLabel')
            self.workshop_label.grid(row=0, column=1, sticky="e", padx=(5, 0))

            logging.info("GUI components initialized successfully")
            
        except Exception as e:
            logging.error(f"Error setting up GUI components: {e}")
            raise
    
    def _setup_module_stats(self):
        """Set up the module statistics UI in the Modules tab"""
        try:
            # Module Status Section
            module_status_container = ttk.Frame(self.modules_stats_frame)
            module_status_container.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            
            # Add a header for the module status section
            module_header = ttk.Label(module_status_container, text="Module Status", font=("Segoe UI", 10, "bold"))
            module_header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
            
            # Create indicators for each module
            # SWEP Detector
            swep_module_frame = ttk.Frame(module_status_container)
            swep_module_frame.grid(row=1, column=0, sticky="w", padx=10, pady=2)
            swep_module_frame.columnconfigure(0, weight=1)
            swep_module_frame.columnconfigure(1, weight=1)
            
            ttk.Label(swep_module_frame, text="SWEP Detector: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.swep_module_status = ttk.Label(swep_module_frame, text="Inactive", foreground="#888888")
            self.swep_module_status.grid(row=0, column=1, sticky="w", padx=(5, 0))
            
            # Texture Extractor
            texture_module_frame = ttk.Frame(module_status_container)
            texture_module_frame.grid(row=1, column=1, sticky="w", padx=10, pady=2)
            texture_module_frame.columnconfigure(0, weight=1)
            texture_module_frame.columnconfigure(1, weight=1)
            
            ttk.Label(texture_module_frame, text="Texture Extractor: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.texture_module_status = ttk.Label(texture_module_frame, text="Inactive", foreground="#888888")
            self.texture_module_status.grid(row=0, column=1, sticky="w", padx=(5, 0))
            
            # Module Performance Stats
            module_perf_container = ttk.Frame(self.modules_stats_frame)
            module_perf_container.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
            
            # Add a header for the performance section
            perf_header = ttk.Label(module_perf_container, text="Module Performance", font=("Segoe UI", 10, "bold"))
            perf_header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
            
            # SWEP Detector Performance
            swep_perf_frame = ttk.Frame(module_perf_container)
            swep_perf_frame.grid(row=1, column=0, sticky="w", padx=10, pady=2)
            swep_perf_frame.columnconfigure(0, weight=1)
            swep_perf_frame.columnconfigure(1, weight=1)
            
            ttk.Label(swep_perf_frame, text="SWEP Processing Time: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.swep_time_label = ttk.Label(swep_perf_frame, text="0:00:00", style='StatValue.TLabel')
            self.swep_time_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Texture Extractor Performance
            texture_perf_frame = ttk.Frame(module_perf_container)
            texture_perf_frame.grid(row=1, column=1, sticky="w", padx=10, pady=2)
            texture_perf_frame.columnconfigure(0, weight=1)
            texture_perf_frame.columnconfigure(1, weight=1)
            
            ttk.Label(texture_perf_frame, text="Texture Processing Time: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.texture_time_label = ttk.Label(texture_perf_frame, text="0:00:00", style='StatValue.TLabel')
            self.texture_time_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Memory Usage
            memory_frame = ttk.Frame(module_perf_container)
            memory_frame.grid(row=2, column=0, sticky="w", padx=10, pady=2)
            memory_frame.columnconfigure(0, weight=1)
            memory_frame.columnconfigure(1, weight=1)
            
            ttk.Label(memory_frame, text="Memory Usage: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.memory_usage_label = ttk.Label(memory_frame, text="0 MB", style='StatValue.TLabel')
            self.memory_usage_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # CPU Usage
            cpu_frame = ttk.Frame(module_perf_container)
            cpu_frame.grid(row=2, column=1, sticky="w", padx=10, pady=2)
            cpu_frame.columnconfigure(0, weight=1)
            cpu_frame.columnconfigure(1, weight=1)
            
            ttk.Label(cpu_frame, text="CPU Usage: ", style='StatLabel.TLabel').grid(row=0, column=0, sticky="w")
            self.cpu_usage_label = ttk.Label(cpu_frame, text="0%", style='StatValue.TLabel')
            self.cpu_usage_label.grid(row=0, column=1, sticky="e", padx=(5, 0))
            
            # Initialize module-specific timing variables
            self.swep_start_time = None
            self.swep_end_time = None
            self.texture_start_time = None
            self.texture_end_time = None
            
        except Exception as e:
            logging.error(f"Error setting up module stats UI: {e}")
    
    def _update_stats(self):
        """Update statistics display"""
        try:
            # Update file counts with formatting for better readability
            self.stats_labels['found'].config(text=f"{self.files_found:,}")
            self.stats_labels['files'].config(text=f"{self.processed_files:,}")
            
            # Update file count in progress bar section
            self.file_count_label.config(text=f"Processing {self.processed_files:,} of {self.total_files:,} files")
            self.stats_labels['vmts'].config(text=f"{self.vmt_files_created:,}")
            self.stats_labels['deleted'].config(text=f"{self.vmt_files_deleted:,}")  # Add deletion counter
            self.stats_labels['c4_sounds'].config(text=f"{self.c4_sounds_replaced:,}")  # Add C4 sounds counter
            
            # Update success rate
            if self.processed_files > 0:
                success_rate = ((self.processed_files - self.errors) / self.processed_files) * 100
                self.stats_labels['rate'].config(text=f"{success_rate:.1f}%")
            else:
                self.stats_labels['rate'].config(text="0%")
            
            # Update processing time
            if self.start_time:
                elapsed = time.time() - self.start_time
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                self.stats_labels['time'].config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                self.stats_labels['time'].config(text="00:00:00")
            
            # Update error count
            self.stats_labels['errors'].config(text=str(self.errors))
            
            # Update SWEP stats with better formatting
            if hasattr(self, 'sweps_detected') and self.sweps_detected > 0:
                self.sweps_detected_label.config(text=f"{self.sweps_detected:,}")
            if hasattr(self, 'lua_files_processed') and self.lua_files_processed > 0:
                self.lua_files_label.config(text=f"{self.lua_files_processed:,}")
            if hasattr(self, 'lua_cache_files_processed') and self.lua_cache_files_processed > 0:
                self.lua_cache_label.config(text=f"{self.lua_cache_files_processed:,}")
            if hasattr(self, 'swep_textures_found') and self.swep_textures_found > 0:
                self.swep_textures_label.config(text=f"{self.swep_textures_found:,}")
            if hasattr(self, 'swep_models_found') and self.swep_models_found > 0:
                self.swep_models_label.config(text=f"{self.swep_models_found:,}")
            if hasattr(self, 'addons_scanned') and self.addons_scanned > 0:
                self.addons_label.config(text=f"{self.addons_scanned:,}")
            if hasattr(self, 'workshop_items_scanned') and self.workshop_items_scanned > 0:
                self.workshop_label.config(text=f"{self.workshop_items_scanned:,}")
            if hasattr(self, 'current_swep_phase') and self.current_swep_phase:
                # Update only the progress bar phase label
                self.current_phase_label.config(text=f"{self.current_swep_phase}")
            
            # No need to update summary labels as they're now part of the stats_labels
            
            # Update module status indicators
            module_config = self.config.get("MODULES", {})
            swep_detector_enabled = module_config.get("swep_detector", True)
            texture_extractor_enabled = module_config.get("texture_extractor", True)
            
            # Update SWEP detector status
            if swep_detector_enabled:
                self.swep_module_status.config(text="Active", foreground="#009900")
            else:
                self.swep_module_status.config(text="Disabled", foreground="#CC0000")
                
            # Update Texture extractor status
            if texture_extractor_enabled:
                self.texture_module_status.config(text="Active", foreground="#009900")
            else:
                self.texture_module_status.config(text="Disabled", foreground="#CC0000")
                
            # Update module timing information
            if self.swep_start_time:
                if self.swep_end_time:
                    swep_elapsed = self.swep_end_time - self.swep_start_time
                else:
                    swep_elapsed = time.time() - self.swep_start_time
                    
                hours = int(swep_elapsed // 3600)
                minutes = int((swep_elapsed % 3600) // 60)
                seconds = int(swep_elapsed % 60)
                self.swep_time_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            if self.texture_start_time:
                if self.texture_end_time:
                    texture_elapsed = self.texture_end_time - self.texture_start_time
                else:
                    texture_elapsed = time.time() - self.texture_start_time
                    
                hours = int(texture_elapsed // 3600)
                minutes = int((texture_elapsed % 3600) // 60)
                seconds = int(texture_elapsed % 60)
                self.texture_time_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
            # Update memory and CPU usage
            try:
                # Import psutil only once at the beginning of the application
                if not hasattr(self, 'psutil_available'):
                    try:
                        import psutil
                        self.psutil = psutil
                        self.psutil_available = True
                        self.psutil_process = psutil.Process()
                        logging.info("psutil is available for system monitoring")
                    except ImportError:
                        self.psutil_available = False
                        logging.warning("psutil is not available, system monitoring will be disabled")
                        # Update labels to indicate monitoring is unavailable
                        self.memory_usage_label.config(text="N/A")
                        self.cpu_usage_label.config(text="N/A")
                
                # Only try to get metrics if psutil is available
                if hasattr(self, 'psutil_available') and self.psutil_available:
                    # Get memory usage
                    memory_info = self.psutil_process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                    self.memory_usage_label.config(text=f"{memory_mb:.1f} MB")
                    
                    # Get CPU usage - don't use interval here as it blocks the UI
                    # Instead, just get the current value which is based on previous measurements
                    cpu_percent = self.psutil_process.cpu_percent(interval=None)
                    
                    # Get the number of logical CPUs to calculate per-core percentage
                    if not hasattr(self, 'cpu_count'):
                        self.cpu_count = self.psutil.cpu_count(logical=True)
                        logging.info(f"Detected {self.cpu_count} logical CPU cores")
                    
                    # Calculate per-core percentage (will be >100% if using multiple cores)
                    raw_percent = cpu_percent
                    
                    # Calculate normalized percentage (0-100% range)
                    if self.cpu_count > 0:
                        normalized_percent = min(100, cpu_percent / self.cpu_count)
                    else:
                        normalized_percent = cpu_percent
                    
                    # Display both raw and normalized percentages
                    self.cpu_usage_label.config(text=f"{normalized_percent:.1f}% ({raw_percent:.1f}% total)")
            except Exception as e:
                logging.error(f"Error updating system metrics: {e}")
                self.memory_usage_label.config(text="Error")
                self.cpu_usage_label.config(text="Error")
            
        except Exception as e:
            logging.error(f"Error updating stats: {e}")
            # Don't re-raise the exception to prevent GUI crashes
    
    def _update_gui(self):
        """Update GUI elements periodically"""
        try:
            current_time = time.time()
            
            # Update time display independently
            if self.is_processing and self.start_time:
                elapsed_time = current_time - self.start_time
                hours = int(elapsed_time // 3600)
                minutes = int((elapsed_time % 3600) // 60)
                seconds = int(elapsed_time % 60)
                
                self.time_label.config(text=f"Time: {hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # Update progress percentage labels
                overall_percent = int(self.progress_bar["value"])
                action_percent = int(self.action_progress_bar["value"])
                self.overall_percent_label.config(text=f"{overall_percent}%")
                self.action_percent_label.config(text=f"{action_percent}%")
            
            # Force update if enough time has passed
            if current_time - self.last_update >= self.update_threshold:
                # Update stats
                self._update_stats()
                
                # Ensure start button is enabled if not processing
                if not self.is_processing and self.start_button['state'] == 'disabled' and self.preload_complete:
                    self.start_button.config(state="normal")
                    logging.info("Re-enabled start button")
                
                self.window.update_idletasks()
                self.last_update = current_time
            
            # Schedule next update
            self.window.after(100, self._update_gui)
            
        except Exception as e:
            logging.error(f"Error updating GUI: {e}")
            # Ensure we keep updating even if there's an error
            self.window.after(100, self._update_gui)
    
    def _preload_data(self):
        """Preload Steam and game paths data."""
        try:
            # Reset progress bars
            self.progress_bar["value"] = 0
            self.action_progress_bar["value"] = 0
            
            # Step 1: Find Steam installation (10% of overall progress)
            self.status_label.config(text="Finding Steam installation...")
            self.progress_bar["value"] = 0
            self.action_progress_bar["value"] = 0
            self.window.update_idletasks()
            
            self.steam_path = find_steam_path()
            
            if not self.steam_path:
                self.status_label.config(text="Error: Could not find Steam installation!")
                return
            
            self.progress_bar["value"] = 10
            self.action_progress_bar["value"] = 100
            self.window.update_idletasks()
            
            # Step 2: Find Source engine games (20% of overall progress)
            self.status_label.config(text="Finding Source engine games...")
            self.action_progress_bar["value"] = 0
            self.window.update_idletasks()
            
            self.game_paths = find_game_paths(self.steam_path)
            
            if not self.game_paths:
                self.status_label.config(text="Error: Could not find any Source engine games!")
                return
            
            self.progress_bar["value"] = 30
            self.action_progress_bar["value"] = 100
            self.window.update_idletasks()
            
            # Step 3: Find VPK files (70% of overall progress)
            self.status_label.config(text="Finding VPK files...")
            self.action_progress_bar["value"] = 0
            self.window.update_idletasks()
            
            def update_files_found(count):
                self.files_found = count
                self.total_files = count
                
                # Update action progress based on completed scan tasks
                if hasattr(update_files_found, 'last_task_count') and hasattr(update_files_found, 'total_tasks'):
                    if update_files_found.total_tasks > 0:
                        action_progress = (update_files_found.last_task_count / update_files_found.total_tasks) * 100
                        self.action_progress_bar["value"] = action_progress
                
                # Update overall progress (30% to 30% range for VPK scanning)
                # We don't advance the overall progress during preload anymore
                self.progress_bar["value"] = 30
                self.window.update_idletasks()
            
            # Add task tracking attributes to the callback function
            update_files_found.last_task_count = 0
            update_files_found.total_tasks = 0
            
            # Custom callback for task progress
            def task_progress_callback(completed, total):
                update_files_found.last_task_count = completed
                update_files_found.total_tasks = total
                
                # Update scan task progress in the UI
                if hasattr(self, 'scan_task_label'):
                    self.scan_task_label.config(text=f"Completed {completed}/{total} scan tasks")
            
            # Find VPK files
            self.vpk_files = find_vpk_files(
                self.game_paths, 
                gui_callback=update_files_found,
                should_continue=lambda: not self.is_processing,
                task_progress_callback=task_progress_callback
            )
            
            self.preload_complete = True
            self.status_label.config(text=f"Ready to process {len(self.vpk_files)} files")
            self.start_button.config(state="normal")
            
            # Update scan task display with final count
            if hasattr(self, 'scan_task_label'):
                self.scan_task_label.config(text=f"Found {len(self.vpk_files)} VPK files total")
                
            # Set progress values to indicate preload is complete, but not the whole process
            self.progress_bar["value"] = 25  # Only 25% of the overall process is done after preload
            self.action_progress_bar["value"] = 100
            self.window.update_idletasks()
            
        except Exception as e:
            logging.error(f"Error preloading data: {e}")
            self.status_label.config(text=f"Error preloading data: {e}")
    
    def start_processing(self):
        """Start processing files."""
        if self.is_processing:
            return
            
        if not self.preload_complete:
            self.status_label.config(text="Error: Preload not complete!")
            return
            
        # Reload config to ensure we have the latest settings
        from src.config.config_manager import load_config
        self.config = load_config()
        
        # Log module settings at start time
        module_config = self.config.get("MODULES", {})
        logging.info(f"[START] Module settings: {module_config}")
        logging.info(f"[START] SWEP detector enabled: {module_config.get('swep_detector', True)}")
        logging.info(f"[START] Texture extractor enabled: {module_config.get('texture_extractor', True)}")
            
        self.is_processing = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.settings_button.config(state="disabled")
        
        # Reset counters
        self.processed_files = 0
        self.vmt_files_created = 0
        self.vmt_files_deleted = 0
        self.c4_sounds_replaced = 0
        self.errors = 0
        self.progress_bar["value"] = 0
        
        # Display active modules in the status label
        module_config = self.config.get("MODULES", {})
        swep_detector_enabled = module_config.get("swep_detector", True)
        texture_extractor_enabled = module_config.get("texture_extractor", True)
        
        active_modules = []
        if swep_detector_enabled:
            active_modules.append("SWEP Detector")
        if texture_extractor_enabled:
            active_modules.append("Texture Extractor")
            
        modules_text = ", ".join(active_modules)
        self.status_label.config(text=f"Starting processing with active modules: {modules_text}")
        
        # Update file count and phase in the progress bar section
        self.file_count_label.config(text=f"Ready to process {self.total_files:,} files")
        self.current_phase_label.config(text="Initializing")
        self.window.update_idletasks()
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self._process_task)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def stop_processing(self):
        """Stop processing files."""
        if not self.is_processing:
            return
            
        self.is_processing = False
        self.stop_button.config(state="disabled")
        self.status_label.config(text="Stopping processing...")
    
    def show_settings(self):
        """Show settings dialog."""
        SettingsDialog(self.window)
    
    def _process_task(self):
        """Process files using preloaded data."""
        try:
            if not self.preload_complete:
                self.status_label.config(text="Error: Preload not complete!")
                return

            self.start_time = time.time()
            self.errors = 0
            last_progress_update = time.time()
            
            # Get Garry's Mod path for VMT creation
            gmod_path = self.game_paths.get("GarrysMod")
            if not gmod_path:
                self.status_label.config(text="Error: Garry's Mod path not found!")
                return
                
            gmod_materials = gmod_path / "garrysmod" / "materials"
            all_texture_paths = []
            
            # Initialize services
            file_processor = FileProcessor(self.config)
            vmt_generator = VMTGenerator(self.config)
            
            # Update initial status
            self.status_label.config(text="Scanning VPK files...")
            self.window.update_idletasks()
            
            # Process VPK files in smaller chunks for more frequent updates
            chunk_size = 2  # Reduced chunk size for more frequent updates
            vpk_chunks = [self.vpk_files[i:i + chunk_size] for i in range(0, len(self.vpk_files), chunk_size)]
            
            # Process SWEP detection if both the module and feature are enabled
            module_config = self.config.get("MODULES", {})
            
            # Force reload module config to ensure we have the latest settings
            logging.info(f"Raw module config from config file: {module_config}")
            
            # Explicitly check if the key exists and is False, otherwise default to True
            swep_detector_enabled = True
            if "swep_detector" in module_config and module_config["swep_detector"] is False:
                swep_detector_enabled = False
            
            # Add debug logging to see the actual value
            logging.info(f"SWEP Detector module enabled (after check): {swep_detector_enabled}")
            logging.info(f"Module config: {module_config}")
            
            # Only run SWEP detection if the module is explicitly enabled
            if swep_detector_enabled and self.config.get("SWEP_DETECTION", {}).get("enabled", True):
                # Start timing SWEP detection
                self.swep_start_time = time.time()
                logging.info("Running SWEP detector...")
                self.status_label.config(text="Scanning for SWEPs...")
                self.window.update_idletasks()
                
                # Initialize SWEP detector
                from src.services.swep import SWEPDetector
                swep_detector = SWEPDetector(self.config)
                
                # Set game path
                gmod_path = self.game_paths.get("GarrysMod")
                if gmod_path:
                    # Define progress callback
                    def swep_progress_callback(phase, overall_progress, phase_progress, message):
                        if not self.is_processing:
                            return
                            
                        self.current_swep_phase = phase.replace('_', ' ').title()
                        
                        # Update progress bars
                        overall_percent = 50 + (overall_progress * 15)  # 50-65% range
                        self.progress_bar["value"] = overall_percent
                        self.action_progress_bar["value"] = phase_progress * 100
                        
                        # Update status
                        self.status_label.config(text=f"SWEP Detection: {message}")
                        
                        # Update scan task progress display with SWEP detection details
                        if hasattr(self, 'scan_task_label') and message and 'scan' in message.lower():
                            # Extract task progress information if available
                            if '/' in message:
                                self.scan_task_label.config(text=message)
                        
                        # Update stats from detector
                        stats = swep_detector.get_stats()
                        self.sweps_detected = stats['sweps_detected']
                        self.lua_files_processed = stats['lua_files_processed']
                        self.lua_cache_files_processed = stats['lua_cache_files_processed']
                        self.swep_textures_found = stats['textures_found']
                        self.swep_models_found = stats['models_found']
                        self.addons_scanned = stats['addons_scanned']
                        self.workshop_items_scanned = stats['workshop_items_scanned']
                        
                        self._update_stats()
                        self.window.update_idletasks()
                    
                    # Scan for SWEPs
                    try:
                        swep_detector.scan_for_sweps(gmod_path, progress_callback=swep_progress_callback)
                        
                        # Get final stats
                        stats = swep_detector.get_stats()
                        self.sweps_detected = stats['sweps_detected']
                        self.lua_files_processed = stats['lua_files_processed']
                        self.lua_cache_files_processed = stats['lua_cache_files_processed']
                        self.swep_textures_found = stats['textures_found']
                        self.swep_models_found = stats['models_found']
                        self.addons_scanned = stats['addons_scanned']
                        self.workshop_items_scanned = stats['workshop_items_scanned']
                        
                        # Get texture references and add them to all_texture_paths
                        swep_textures = swep_detector.get_texture_references()
                        if swep_textures:
                            all_texture_paths.extend(swep_textures)
                            logging.info(f"Added {len(swep_textures)} textures from SWEP detection")
                        
                        # End timing SWEP detection
                        self.swep_end_time = time.time()
                        logging.info(f"SWEP detection completed in {self.swep_end_time - self.swep_start_time:.2f} seconds")
                        
                        self._update_stats()
                    except Exception as e:
                        logging.error(f"Error in SWEP detection: {e}")
                        self.errors += 1
                else:
                    logging.warning("Garry's Mod path not found, skipping SWEP detection")
            
            # Check if texture extractor module is enabled
            # Explicitly check if the key exists and is False, otherwise default to True
            texture_extractor_enabled = True
            if "texture_extractor" in module_config and module_config["texture_extractor"] is False:
                texture_extractor_enabled = False
            
            # Add debug logging for texture extractor module
            logging.info(f"Texture Extractor module enabled (after check): {texture_extractor_enabled}")
            
            # Process each VPK chunk if texture extractor is enabled
            if texture_extractor_enabled:
                # Start timing texture extraction
                self.texture_start_time = time.time()
                for chunk_index, vpk_chunk in enumerate(vpk_chunks):
                    if not self.is_processing:
                        break
                        
                    for path in vpk_chunk:
                        if not self.is_processing:
                            break
                            
                        try:
                            current_time = time.time()
                            if current_time - last_progress_update >= 0.5:  # Update less frequently
                                self.status_label.config(text=f"Processing VPK file {self.processed_files + 1} of {self.total_files}")
                                if self.total_files > 0:
                                    # Overall progress: 25% (preload) + up to 25% for VPK processing
                                    progress = 25 + (self.processed_files / self.total_files) * 25
                                    self.progress_bar["value"] = progress
                                    self.action_progress_bar["value"] = (self.processed_files / self.total_files) * 100
                                self._update_stats()
                                self.window.update_idletasks()
                                last_progress_update = current_time
                                
                            textures = file_processor.process_file(path)
                            if textures:
                                all_texture_paths.extend(textures)
                            self.processed_files += 1
                            
                        except Exception as e:
                            logging.error(f"Error processing {path}: {str(e)}")
                        self.errors += 1
                
                # Force update after each chunk
                self._update_stats()
                self.window.update_idletasks()
                
                # End timing texture extraction
                self.texture_end_time = time.time()
                logging.info(f"Texture extraction completed in {self.texture_end_time - self.texture_start_time:.2f} seconds")
                time.sleep(0.01)  # Small delay to prevent GUI freezing
            
            # Create VMT files if we have textures
            if all_texture_paths and self.is_processing:
                total_textures = len(all_texture_paths)
                self.status_label.config(text=f"Creating VMT files (0/{total_textures})")
                self.window.update_idletasks()
                
                vmt_count = 0
                delete_count = 0
                last_vmt_update = time.time()
                created_vmts = []  # Keep track of created VMT paths
                
                for vtf_path in sorted(all_texture_paths):
                    if not self.is_processing:
                        break
                        
                    try:
                        current_time = time.time()
                        if current_time - last_vmt_update >= 0.5:
                            self.status_label.config(text=f"Creating VMT files ({vmt_count}/{total_textures})")
                            # Overall progress: 25% (preload) + 25% (VPK) + 15% (SWEP) + up to 10% for VMT creation
                            progress = 65 + (vmt_count / total_textures) * 10
                            self.progress_bar["value"] = progress
                            self.action_progress_bar["value"] = (vmt_count / total_textures) * 100
                            self.vmt_files_created = vmt_count
                            self.vmt_files_deleted = delete_count
                            self._update_stats()
                            self.window.update_idletasks()
                            last_vmt_update = current_time
                            
                        # Convert vtf_path to vmt_path and ensure we're not creating nested materials folders
                        vmt_path = vtf_path.replace('.vtf', '.vmt')
                        
                        # Remove 'materials/' prefix if it exists to avoid nested folders
                        if vmt_path.lower().startswith('materials/'):
                            vmt_path = vmt_path[len('materials/'):]
                            
                        full_path = os.path.join(gmod_materials, vmt_path)
                        
                        # Create directory structure
                        parent_dir = os.path.dirname(full_path)
                        if not os.path.exists(parent_dir):
                            os.makedirs(parent_dir, exist_ok=True)
                        
                        # Generate VMT content using our simplified VMTGenerator
                        vmt_content, vmt_type = vmt_generator.create_vmt_content(vtf_path)
                        
                        # Write the VMT file
                        if vmt_content and vmt_generator.create_vmt_file(full_path, vmt_content):
                                
                                vmt_count += 1
                                created_vmts.append((full_path, vtf_path))  # Store created VMT path
                                
                    except Exception as e:
                        logging.error(f"Error creating VMT for {vtf_path}: {e}")
                        self.errors += 1
                
                # After creating all VMTs, delete the ones we don't want using smaller batches for better UI responsiveness
                if self.is_processing and created_vmts:
                    total_vmts = len(created_vmts)
                    self.status_label.config(text=f"Cleaning up unwanted VMTs (0/{total_vmts})")
                    self.window.update_idletasks()
                    
                    # Use smaller batches for more frequent UI updates
                    batch_size = 50  # Process 50 VMTs at a time
                    processed = 0
                    last_update_time = time.time()
                    
                    # Create a list to store VMTs that should be deleted
                    to_delete = []
                    
                    # First pass: identify which VMTs should be deleted (this is fast)
                    for full_path, vtf_path in created_vmts:
                        if vmt_generator.should_delete_vmt(vtf_path):
                            to_delete.append(full_path)
                        
                        processed += 1
                        if time.time() - last_update_time > 0.2:  # Update UI every 200ms
                            self.status_label.config(text=f"Analyzing VMTs ({processed}/{total_vmts})")
                            # Overall progress: 25% (preload) + 25% (VPK) + 15% (SWEP) + 10% (VMT creation) + up to 15% for VMT analysis
                            progress = 75 + (processed / total_vmts) * 15
                            self.progress_bar["value"] = progress
                            self.action_progress_bar["value"] = (processed / total_vmts) * 100
                            self.window.update_idletasks()
                            last_update_time = time.time()
                    
                    # Second pass: actually delete the files (using multi-threading for speed)
                    if to_delete:
                        total_to_delete = len(to_delete)
                        self.status_label.config(text=f"Deleting unwanted VMTs (0/{total_to_delete})")
                        self.action_progress_bar["value"] = 0
                        self.window.update_idletasks()
                        
                        # Get the number of threads from config
                        num_threads = self.config.get("PERFORMANCE", {}).get("num_threads", 4)
                        
                        # Split into smaller batches for more frequent updates
                        batches = [to_delete[i:i + batch_size] for i in range(0, len(to_delete), batch_size)]
                        processed = 0
                        
                        # Process batches with progress updates
                        for batch in batches:
                            if not self.is_processing:
                                break
                                
                            # Delete files in this batch using a thread pool
                            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                                # Map each file to a delete operation
                                futures = [executor.submit(os.remove, path) for path in batch if os.path.exists(path)]
                                
                                # Wait for all deletions to complete
                                for future in as_completed(futures):
                                    try:
                                        future.result()  # Get result to catch any exceptions
                                        delete_count += 1
                                    except Exception as e:
                                        logging.error(f"Error deleting VMT: {e}")
                                        self.errors += 1
                            
                            # Update progress after each batch
                            processed += len(batch)
                            self.vmt_files_deleted = delete_count
                            self.status_label.config(text=f"Deleting unwanted VMTs ({processed}/{total_to_delete})")
                            # Overall progress: 25% (preload) + 25% (VPK) + 15% (SWEP) + 10% (VMT creation) + 15% (VMT analysis) + up to 10% for VMT deletion
                            progress = 90 + (processed / total_to_delete) * 10
                            self.progress_bar["value"] = progress
                            self.action_progress_bar["value"] = (processed / total_to_delete) * 100
                            self._update_stats()
                            self.window.update_idletasks()
                            time.sleep(0.01)  # Small delay to allow UI to refresh
            
            # Process C4 sound files if enabled
            c4_sound_paths = file_processor.get_c4_sound_paths()
            if self.config.get("C4_SOUND_REPLACEMENT", {}).get("enabled", False) and c4_sound_paths:
                total_sounds = len(c4_sound_paths)
                
                if total_sounds > 0 and self.is_processing:
                    self.status_label.config(text=f"Replacing C4 sounds (0/{total_sounds})")
                    self.window.update_idletasks()
                    
                    sound_count = 0
                    last_sound_update = time.time()
                    gmod_sounds = gmod_path / "garrysmod" / "sound"
                    
                    for sound_path in sorted(c4_sound_paths):
                        if not self.is_processing:
                            break
                            
                        try:
                            current_time = time.time()
                            if current_time - last_sound_update >= 0.5:
                                self.status_label.config(text=f"Replacing C4 sounds ({sound_count}/{total_sounds})")
                                self.c4_sounds_replaced = sound_count
                                self._update_stats()
                                self.window.update_idletasks()
                                last_sound_update = current_time
                            
                            # Extract the sound file from the VPK
                            for vpk_path in self.vpk_files:
                                try:
                                    import vpk
                                    vpk_package = vpk.open(str(vpk_path))
                                    if sound_path in vpk_package:
                                        # Get the sound file data
                                        sound_data = vpk_package[sound_path].read()
                                        
                                        # Create the output path
                                        if 'sound/' in sound_path.lower():
                                            # Remove 'sound/' prefix if present to get the relative path
                                            rel_path = sound_path[sound_path.lower().find('sound/') + 6:]
                                        else:
                                            rel_path = sound_path
                                        
                                        # Create the output directory structure
                                        output_path = gmod_sounds / rel_path
                                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                                        
                                        # Write the sound file
                                        with open(output_path, 'wb') as f:
                                            f.write(sound_data)
                                        
                                        sound_count += 1
                                        break
                                except Exception as e:
                                    logging.error(f"Error extracting sound file {sound_path}: {e}")
                                    continue
                        except Exception as e:
                            logging.error(f"Error replacing C4 sound {sound_path}: {e}")
                            self.errors += 1
                    
                    # Update final count
                    self.c4_sounds_replaced = sound_count
                    self._update_stats()
            
            if self.is_processing:
                # Format completion message
                elapsed = time.time() - self.start_time
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                
                completion_msg = (
                    f"Operation Complete!\n"
                    f"Created: {self.vmt_files_created:,} VMTs\n"
                    f"Deleted: {self.vmt_files_deleted:,} VMTs\n"
                    f"Time: {time_str}"
                )
                
                # Show a completion dialog with the icon
                try:
                    if hasattr(self, 'icon'):
                        completion_window = tk.Toplevel(self.window)
                        completion_window.title("Operation Complete")
                        completion_window.geometry("400x250")
                        completion_window.resizable(False, False)
                        completion_window.transient(self.window)  # Set as transient to main window
                        completion_window.grab_set()  # Make modal
                        
                        # Set the icon
                        completion_window.iconphoto(True, self.icon)
                        
                        # Center the dialog
                        completion_window.update_idletasks()
                        width = completion_window.winfo_width()
                        height = completion_window.winfo_height()
                        x = (self.window.winfo_width() // 2) - (width // 2) + self.window.winfo_x()
                        y = (self.window.winfo_height() // 2) - (height // 2) + self.window.winfo_y()
                        completion_window.geometry(f"{width}x{height}+{x}+{y}")
                        
                        # Create a frame with padding
                        frame = ttk.Frame(completion_window, padding=20)
                        frame.pack(fill="both", expand=True)
                        
                        # Add icon at the top
                        icon_label = ttk.Label(frame, image=self.icon.subsample(2, 2))
                        icon_label.pack(pady=(0, 15))
                        
                        # Add completion message
                        msg_label = ttk.Label(
                            frame, 
                            text=completion_msg,
                            justify=tk.CENTER,
                            font=('Segoe UI', 10, 'bold')
                        )
                        msg_label.pack(pady=10)
                        
                        # Add OK button
                        ok_button = ttk.Button(
                            frame, 
                            text="OK", 
                            command=completion_window.destroy,
                            style='Primary.TButton',
                            width=10
                        )
                        ok_button.pack(pady=10)
                except Exception as e:
                    logging.error(f"Error showing completion dialog: {e}")
                
                # Now set both progress bars to 100% since we're truly done
                self.progress_bar["value"] = 100
                self.action_progress_bar["value"] = 100
                self.window.update_idletasks()
                
                self.status_label.config(
                    text=completion_msg,
                    justify=tk.CENTER,
                    font=('Helvetica', 10, 'bold')
                )
            else:
                self.status_label.config(
                    text="Processing stopped",
                    justify=tk.CENTER,
                    font=('Helvetica', 10)
                )
                
            # Re-enable buttons
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.settings_button.config(state="normal")
            self.is_processing = False
                
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            logging.error(f"Processing error: {str(e)}")
            self.errors += 1
            
            # Re-enable buttons
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.settings_button.config(state="normal")
            self.is_processing = False
