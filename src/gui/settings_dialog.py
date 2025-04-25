"""
Settings Dialog for Source Engine Asset Manager GUI
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import logging
import threading

from src.config.config_manager import load_config, save_config, save_settings_to_file
from src.services.update_service import UpdateService

class SettingsDialog:
    """Dialog for configuring application settings."""
    
    def __init__(self, parent):
        """Initialize the settings dialog."""
        self.config = load_config()
        self.skip_vars = []  # Initialize skip_vars as an empty list
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog on parent
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 600) // 2
        self.dialog.geometry(f"500x600+{x}+{y}")
        
        # Create main container with scrollbar
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create frame for settings
        self.settings_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.settings_frame, anchor="nw")
        
        # Add settings sections
        self._add_module_settings()  # Add the new module settings section first
        self._add_update_settings()
        self._add_backup_settings()
        self._add_transparency_settings()
        self._add_weapon_color_settings()
        self._add_c4_sound_settings()
        self._add_prop_shader_settings()
        self._add_deletion_settings()
        self._add_performance_settings()
        self._add_logging_settings()
        
        # Add save button at bottom
        save_button = ttk.Button(self.dialog, text="Save Settings", command=self._save_settings)
        save_button.pack(pady=20)
        
        # Update scroll region
        self.settings_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Add mousewheel scrolling
        self._mousewheel_binding = self.dialog.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
        
        # Make sure we unbind the mousewheel when the dialog is closed
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)
    
    def _add_section(self, title):
        """Add a new settings section with a title"""
        frame = ttk.LabelFrame(self.settings_frame, text=title, padding="10")
        frame.pack(fill=tk.X, padx=5, pady=5)
        return frame
    
    def _add_module_settings(self):
        """Add module settings section to enable/disable specific modules."""
        frame = self._add_section("Module Settings")
        
        # Get module settings from config
        module_config = self.config.get("MODULES", {})
        logging.info(f"Loading module settings in dialog: {module_config}")
        
        # Create variables for module settings
        self.module_vars = {
            'swep_detector': tk.BooleanVar(value=module_config.get('swep_detector', True)),
            'texture_extractor': tk.BooleanVar(value=module_config.get('texture_extractor', True))
        }
        
        # Log the initial values
        logging.info(f"Initial SWEP detector setting: {self.module_vars['swep_detector'].get()}")
        logging.info(f"Initial Texture extractor setting: {self.module_vars['texture_extractor'].get()}")
        
        # Create module settings controls with a highlighted background
        module_title_frame = ttk.Frame(frame)
        module_title_frame.pack(fill=tk.X, pady=(0, 5))
        
        title_label = ttk.Label(module_title_frame, text="Enable or disable specific modules:", font=("Segoe UI", 9, "bold"))
        title_label.pack(anchor="w")
        
        # SWEP Detector module checkbox with custom styling
        swep_frame = ttk.Frame(frame, style="ModuleOption.TFrame")
        swep_frame.pack(fill=tk.X, pady=4, padx=5)
        
        swep_cb = ttk.Checkbutton(swep_frame, text="SWEP Detector", variable=self.module_vars['swep_detector'])
        swep_cb.pack(side=tk.LEFT)
        ttk.Label(swep_frame, text="(Scans for weapon scripts and extracts textures)", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(10, 0))
        
        # Add trace to log changes
        def on_swep_change(*args):
            logging.info(f"SWEP detector setting changed to: {self.module_vars['swep_detector'].get()}")
        self.module_vars['swep_detector'].trace_add("write", on_swep_change)
        
        # Texture Extractor module checkbox
        texture_frame = ttk.Frame(frame, style="ModuleOption.TFrame")
        texture_frame.pack(fill=tk.X, pady=4, padx=5)
        
        texture_cb = ttk.Checkbutton(texture_frame, text="Texture Extractor", variable=self.module_vars['texture_extractor'])
        texture_cb.pack(side=tk.LEFT)
        ttk.Label(texture_frame, text="(Extracts textures from VPK, BSP, and GMA files)", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(10, 0))
        
        # Add trace to log changes
        def on_texture_change(*args):
            logging.info(f"Texture extractor setting changed to: {self.module_vars['texture_extractor'].get()}")
        self.module_vars['texture_extractor'].trace_add("write", on_texture_change)
        
        # Add a note about module dependencies with better visibility
        note_frame = ttk.Frame(frame)
        note_frame.pack(fill=tk.X, pady=(10, 0))
        note_label = ttk.Label(note_frame, 
                              text="Note: Changes to module settings take effect when you click Start.", 
                              font=("Segoe UI", 8, "italic"), 
                              foreground="#CC0000")
        note_label.pack(anchor="w")
        
    def _add_update_settings(self):
        """Add update settings section with Check for Updates button."""
        frame = self._add_section("Update Settings")
        
        # Get update settings from config
        update_config = self.config.get("UPDATE", {})
        
        self.update_vars = {
            'enabled': tk.BooleanVar(value=update_config.get('enabled', True)),
            'auto_download': tk.BooleanVar(value=update_config.get('auto_download', True)),
            'include_beta': tk.BooleanVar(value=update_config.get('include_beta', False)),
            'backup_before_update': tk.BooleanVar(value=update_config.get('backup_before_update', True))
        }
        
        # Create update settings controls
        ttk.Checkbutton(frame, text="Enable Automatic Updates", variable=self.update_vars['enabled']).pack(anchor="w")
        ttk.Checkbutton(frame, text="Auto-download Updates", variable=self.update_vars['auto_download']).pack(anchor="w")
        ttk.Checkbutton(frame, text="Include Beta Versions", variable=self.update_vars['include_beta']).pack(anchor="w")
        ttk.Checkbutton(frame, text="Backup Before Update", variable=self.update_vars['backup_before_update']).pack(anchor="w")
        
        # Add separator
        ttk.Separator(frame, orient='horizontal').pack(fill='x', padx=5, pady=10)
        
        # Add Check for Updates button
        check_updates_button = ttk.Button(frame, text="Check for Updates Now", command=self._check_for_updates)
        check_updates_button.pack(pady=5)
        
        # Add status label
        self.update_status_var = tk.StringVar(value="")
        status_label = ttk.Label(frame, textvariable=self.update_status_var, wraplength=400)
        status_label.pack(pady=5)
        
    def _check_for_updates(self):
        """Check for updates and show the result to the user."""
        # Update status
        self.update_status_var.set("Checking for updates...")
        
        # Create update service with current config
        update_service = UpdateService(self.config)
        
        # Function to run in thread
        def check_updates_thread():
            try:
                # Check for updates
                update_available, latest_version, release_notes = update_service.check_for_updates()
                
                if update_available:
                    # Show update available message
                    self.update_status_var.set(f"Update available: v{latest_version}")
                    
                    # Ask if user wants to update now
                    if messagebox.askyesno("Update Available", 
                                          f"A new version ({latest_version}) is available!\n\n" +
                                          f"Release Notes:\n{release_notes[:300]}...\n\n" +
                                          "Do you want to update now?"):
                        
                        # Update status
                        self.update_status_var.set(f"Downloading update v{latest_version}...")
                        
                        # Download update
                        if update_service.download_update(latest_version):
                            self.update_status_var.set(f"Applying update v{latest_version}...")
                            
                            # Apply update
                            if update_service.apply_update(latest_version):
                                messagebox.showinfo("Update Complete", 
                                                  f"Update to version {latest_version} completed successfully.\n\n" +
                                                  "The application will now restart.")
                                
                                # Restart application
                                update_service.restart_application()
                            else:
                                self.update_status_var.set("Failed to apply update.")
                                messagebox.showerror("Update Failed", 
                                                   "Failed to apply update. Please try again later or update manually.")
                        else:
                            self.update_status_var.set("Failed to download update.")
                            messagebox.showerror("Update Failed", 
                                               "Failed to download update. Please check your internet connection and try again.")
                else:
                    # Show no update available message
                    current_version = update_service.current_version
                    self.update_status_var.set(f"You have the latest version (v{current_version}).") 
                    messagebox.showinfo("No Updates Available", 
                                      f"You have the latest version (v{current_version}).") 
            except Exception as e:
                # Show error message
                self.update_status_var.set(f"Error checking for updates: {str(e)}")
                logging.error(f"Error checking for updates: {e}")
                messagebox.showerror("Update Error", f"Error checking for updates: {str(e)}")
        
        # Start update check in background thread
        update_thread = threading.Thread(target=check_updates_thread)
        update_thread.daemon = True
        update_thread.start()
    
    # Texture settings section removed as we're not processing textures
    
    def _add_backup_settings(self):
        """Add backup settings section."""
        frame = self._add_section("Backup Settings")
        
        # Get backup settings from config
        backup = self.config.get("BACKUP", {})
        
        self.backup_vars = {
            'enabled': tk.BooleanVar(value=backup.get('enabled', True)),
            'compression': tk.BooleanVar(value=backup.get('compression', True)),
            'max_backups': tk.StringVar(value=str(backup.get('max_backups', 5))),
            'include_cfg': tk.BooleanVar(value=backup.get('include_cfg', True)),
            'include_materials': tk.BooleanVar(value=backup.get('include_materials', True))
        }
        
        ttk.Checkbutton(frame, text="Enable Backups", variable=self.backup_vars['enabled']).pack(anchor="w")
        ttk.Checkbutton(frame, text="Use Compression", variable=self.backup_vars['compression']).pack(anchor="w")
        
        max_frame = ttk.Frame(frame)
        max_frame.pack(fill=tk.X, pady=5)
        ttk.Label(max_frame, text="Max Backups:").pack(side=tk.LEFT)
        ttk.Entry(max_frame, textvariable=self.backup_vars['max_backups'], width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(frame, text="Include Config Files", variable=self.backup_vars['include_cfg']).pack(anchor="w")
        ttk.Checkbutton(frame, text="Include Material Files", variable=self.backup_vars['include_materials']).pack(anchor="w")
    
    def _add_transparency_settings(self):
        """Add transparency settings section."""
        frame = self._add_section("Transparency Settings")
        
        # Get transparency settings from config
        transparency = self.config.get("TRANSPARENCY", {})
        
        # Ensure we're using primitive values
        default_alpha = str(transparency.get('default_alpha', 0.5))
        weapon_alpha = str(transparency.get('weapon_alpha', 1.0))
        effect_alpha = str(transparency.get('effect_alpha', 0.5))
        enable_fade = bool(transparency.get('enable_fade', True))
        
        self.transparency_vars = {
            'default_alpha': tk.StringVar(value=default_alpha),
            'weapon_alpha': tk.StringVar(value=weapon_alpha),
            'effect_alpha': tk.StringVar(value=effect_alpha),
            'enable_fade': tk.BooleanVar(value=enable_fade)
        }
        
        # Create labeled entries for alpha values
        for label, key in [
            ("Default Alpha:", 'default_alpha'),
            ("Weapon Alpha:", 'weapon_alpha'),
            ("Effect Alpha:", 'effect_alpha')
        ]:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=self.transparency_vars[key], width=10).pack(side=tk.LEFT, padx=5)
            
        ttk.Checkbutton(frame, text="Enable Distance Fade", variable=self.transparency_vars['enable_fade']).pack(anchor="w")
    
    def _add_weapon_color_settings(self):
        """Add weapon color settings section."""
        frame = self._add_section("Weapon Colors")
        
        # Get weapon colors from config
        weapon_colors = self.config.get("WEAPON_COLORS", {})
        
        # Create notebook for weapon categories
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True, pady=10)
        
        # Initialize weapon color variables
        self.weapon_vars = {}
        
        # Add tab for each weapon category
        for category, config in weapon_colors.items():
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=config.get('name', category.title()))
            
            # Enable checkbox for category - ensure we're using primitive values
            enabled_value = bool(config.get('enabled', False))
            color_value = str(config.get('color', '[1 1 1]'))
            
            self.weapon_vars[category] = {
                'enabled': tk.BooleanVar(value=enabled_value),
                'color': tk.StringVar(value=color_value),
                'patterns': []
            }
            
            # Enable/disable checkbox
            ttk.Checkbutton(
                tab,
                text=f"Enable {config.get('name', category.title())} Coloring",
                variable=self.weapon_vars[category]['enabled']
            ).pack(anchor="w", pady=5)
            
            # Color input
            color_frame = ttk.Frame(tab)
            color_frame.pack(fill="x", pady=5)
            ttk.Label(color_frame, text="Color (RGB):").pack(side="left", padx=5)
            ttk.Entry(
                color_frame,
                textvariable=self.weapon_vars[category]['color'],
                width=15
            ).pack(side="left", padx=5)
            
            # Pattern list
            patterns_frame = ttk.LabelFrame(tab, text="Patterns", padding=5)
            patterns_frame.pack(fill="both", expand=True)
            
            # Add existing patterns - ensure we're using a list of strings
            patterns = config.get('patterns', [])
            if not isinstance(patterns, list):
                patterns = []
                
            for pattern in patterns:
                var = tk.StringVar(value=str(pattern))
                self.weapon_vars[category]['patterns'].append(var)
                entry = ttk.Entry(patterns_frame, textvariable=var)
                entry.pack(fill="x", pady=2)
            
            # Add button for new patterns
            ttk.Button(
                patterns_frame,
                text="Add Pattern",
                command=lambda c=category: self._add_weapon_pattern(c)
            ).pack(pady=5)
    
    def _add_weapon_pattern(self, category):
        """Add a new pattern entry to the specified weapon category."""
        var = tk.StringVar()
        self.weapon_vars[category]['patterns'].append(var)
        notebook = self.dialog.winfo_children()[0].winfo_children()[-1]
        tab = notebook.select()
        patterns_frame = notebook.winfo_children()[notebook.index(tab)].winfo_children()[2]  # Adjust index based on frame order
        ttk.Entry(patterns_frame, textvariable=var).pack(fill="x", pady=2)
    
    def _add_c4_sound_settings(self):
        """Add C4 sound replacement settings section."""
        frame = self._add_section("C4 Sound Replacement")
        
        # Get C4 sound settings from config
        c4_sound = self.config.get("C4_SOUND_REPLACEMENT", {})
        
        # Enable/disable checkbox - ensure we're using a primitive boolean value
        enabled_value = bool(c4_sound.get('enabled', True))
        self.c4_sound_enabled_var = tk.BooleanVar(value=enabled_value)
        ttk.Checkbutton(
            frame,
            text="Enable C4 Sound Replacement",
            variable=self.c4_sound_enabled_var
        ).pack(anchor="w", pady=5)
        
        # Preserve paths checkbox - ensure we're using a primitive boolean value
        preserve_paths_value = bool(c4_sound.get('preserve_paths', True))
        self.c4_sound_preserve_paths_var = tk.BooleanVar(value=preserve_paths_value)
        ttk.Checkbutton(
            frame,
            text="Preserve Relative Paths",
            variable=self.c4_sound_preserve_paths_var
        ).pack(anchor="w", pady=5)
        
        # Sound file selection
        sound_file_frame = ttk.Frame(frame)
        sound_file_frame.pack(fill="x", pady=5)
        ttk.Label(sound_file_frame, text="Replacement Sound:").pack(side="left", padx=5)
        
        # Get the sound file path with a default
        sound_file = str(c4_sound.get('sound_file', 'npc/zombie/zombie_pain1.wav'))
        self.c4_sound_file_var = tk.StringVar(value=sound_file)
        ttk.Entry(sound_file_frame, textvariable=self.c4_sound_file_var, width=30).pack(side="left", padx=5)
        
        # Add help text for sound file
        ttk.Label(
            frame, 
            text="Tip: Try sounds like 'npc/zombie/zombie_pain1.wav' or\n'npc/headcrab/headcrab_scream1.wav' from HL2 VPK files.",
            justify="left",
            font=("TkDefaultFont", 8, "italic")
        ).pack(anchor="w", pady=2)
        
        # Pattern list
        patterns_frame = ttk.LabelFrame(frame, text="Sound Patterns", padding=5)
        patterns_frame.pack(fill="both", expand=True, pady=5)
        
        # Add existing patterns - ensure we're using a list of strings
        self.c4_sound_patterns_vars = []
        patterns = c4_sound.get('patterns', [])
        if not isinstance(patterns, list):
            patterns = []
            
        for pattern in patterns:
            var = tk.StringVar(value=str(pattern))
            self.c4_sound_patterns_vars.append(var)
            entry = ttk.Entry(patterns_frame, textvariable=var)
            entry.pack(fill="x", pady=2)
        
        # Add button for new patterns
        ttk.Button(
            patterns_frame,
            text="Add Pattern",
            command=self._add_c4_sound_pattern
        ).pack(pady=5)
        
        # Help text
        ttk.Label(
            frame, 
            text="This will replace all C4 sounds as direct WAV files\nin the sounds folder while preserving relative paths.",
            justify="center"
        ).pack(pady=10)
    
    def _add_c4_sound_pattern(self):
        """Add a new pattern entry for C4 sound replacement."""
        var = tk.StringVar(value="")
        self.c4_sound_patterns_vars.append(var)
        
        # Find the patterns frame
        for child in self.settings_frame.winfo_children():
            if isinstance(child, ttk.Labelframe) and child.winfo_children() and \
               "C4 Sound Replacement" in child.winfo_children()[0].cget("text"):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.Labelframe) and "Sound Patterns" in subchild.cget("text"):
                        entry = ttk.Entry(subchild, textvariable=var)
                        entry.pack(fill="x", pady=2)
                        entry.focus_set()
                        break
    
    def _add_prop_shader_settings(self):
        """Add prop shader settings section."""
        frame = self._add_section("Prop Shader Settings")
        
        # Get prop shader settings from config
        prop_shader = self.config.get("PROP_SHADER", {})
        
        # Enable/disable checkbox - ensure we're using a primitive boolean value
        enabled_value = bool(prop_shader.get('enabled', True))
        self.prop_shader_enabled_var = tk.BooleanVar(value=enabled_value)
        ttk.Checkbutton(
            frame,
            text="Enable Prop Shader Changes",
            variable=self.prop_shader_enabled_var
        ).pack(anchor="w", pady=5)
        
        # Shader type selection
        shader_frame = ttk.Frame(frame)
        shader_frame.pack(fill="x", pady=5)
        
        # Ensure we're using a primitive boolean value
        lightmapped_value = bool(prop_shader.get('use_lightmapped', True))
        self.prop_shader_lightmapped_var = tk.BooleanVar(value=lightmapped_value)
        ttk.Checkbutton(
            shader_frame,
            text="Use LightmappedGeneric Shader",
            variable=self.prop_shader_lightmapped_var
        ).pack(anchor="w")
        
        # Alpha value
        alpha_frame = ttk.Frame(frame)
        alpha_frame.pack(fill="x", pady=5)
        ttk.Label(alpha_frame, text="Alpha Value:").pack(side="left", padx=5)
        
        # Ensure we're using a primitive float value converted to string
        try:
            alpha_value = float(prop_shader.get('alpha', 0.9))
        except (ValueError, TypeError):
            alpha_value = 0.9
        self.prop_shader_alpha_var = tk.StringVar(value=str(alpha_value))
        ttk.Entry(
            alpha_frame,
            textvariable=self.prop_shader_alpha_var,
            width=10
        ).pack(side="left", padx=5)
        
        # Pattern list
        patterns_frame = ttk.LabelFrame(frame, text="Prop Patterns", padding=5)
        patterns_frame.pack(fill="both", expand=True, pady=5)
        
        # Add existing patterns - ensure we're using a list of strings
        self.prop_shader_patterns_vars = []
        patterns = prop_shader.get('patterns', [])
        if not isinstance(patterns, list):
            patterns = []
        
        for pattern in patterns:
            var = tk.StringVar(value=str(pattern))
            self.prop_shader_patterns_vars.append(var)
            entry = ttk.Entry(patterns_frame, textvariable=var)
            entry.pack(fill="x", pady=2)
        
        # Add button for new patterns
        ttk.Button(
            patterns_frame,
            text="Add Pattern",
            command=self._add_prop_shader_pattern
        ).pack(pady=5)
        
        # Help text
        ttk.Label(
            frame, 
            text="This will apply the LightmappedGeneric shader to props\nwith the specified alpha value.",
            justify="center"
        ).pack(pady=10)
    
    def _add_prop_shader_pattern(self):
        """Add a new pattern entry for prop shader."""
        var = tk.StringVar(value="")
        self.prop_shader_patterns_vars.append(var)
        
        # Find the patterns frame
        for child in self.settings_frame.winfo_children():
            if isinstance(child, ttk.Labelframe) and child.winfo_children() and \
               "Prop Shader Settings" in child.winfo_children()[0].cget("text"):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.Labelframe) and "Prop Patterns" in subchild.cget("text"):
                        entry = ttk.Entry(subchild, textvariable=var)
                        entry.pack(fill="x", pady=2)
                        entry.focus_set()
                        break

    def _add_deletion_settings(self):
        """Add deletion settings section."""
        frame = self._add_section("Deletion Settings")
        
        # Get deletion settings from config
        deletion = self.config.get("DELETION", {})
        delete_categories = deletion.get("categories", {})
        
        # Enable/disable checkbox - ensure we're using a primitive boolean value
        enabled_value = bool(deletion.get('enabled', True))
        self.deletion_enabled_var = tk.BooleanVar(value=enabled_value)
        ttk.Checkbutton(
            frame,
            text="Enable Deletion of Unwanted Files",
            variable=self.deletion_enabled_var
        ).pack(anchor="w", pady=5)
        
        # Create a frame for the category checkboxes
        categories_frame = ttk.LabelFrame(frame, text="Deletion Categories", padding=5)
        categories_frame.pack(fill="both", expand=True, pady=5)
        
        # Store category variables
        self.deletion_categories = {}
        
        # Add checkboxes for each category
        category_descriptions = {
            "trees": "Trees, foliage, and plants",
            "effects": "Effects, particles, and sprites",
            "ui": "UI elements, HUD, and menus",
            "hands": "Player hands and arms",
            "props": "Props and furniture"
        }
        
        # Create a variable for each category
        for category, desc in category_descriptions.items():
            category_data = delete_categories.get(category, {})
            enabled = bool(category_data.get('enabled', True))
            
            # Create a frame for this category
            cat_frame = ttk.Frame(categories_frame)
            cat_frame.pack(fill="x", pady=2)
            
            # Create the checkbox
            var = tk.BooleanVar(value=enabled)
            self.deletion_categories[category] = {
                'enabled': var,
                'patterns': category_data.get('patterns', [])
            }
            
            ttk.Checkbutton(
                cat_frame,
                text=desc,
                variable=var
            ).pack(side="left", padx=5)
        
        # Custom pattern list
        patterns_frame = ttk.LabelFrame(frame, text="Custom Deletion Patterns", padding=5)
        patterns_frame.pack(fill="both", expand=True, pady=5)
        
        # Add existing patterns - ensure we're using a list of strings
        self.deletion_patterns_vars = []
        patterns = deletion.get('patterns', [])
        if not isinstance(patterns, list):
            patterns = []
            
        for pattern in patterns:
            var = tk.StringVar(value=str(pattern))
            self.deletion_patterns_vars.append(var)
            entry = ttk.Entry(patterns_frame, textvariable=var)
            entry.pack(fill="x", pady=2)
        
        # Add button for new patterns
        ttk.Button(
            patterns_frame,
            text="Add Pattern",
            command=self._add_deletion_pattern
        ).pack(pady=5)
        
        # Help text
        ttk.Label(
            frame, 
            text="Files matching these patterns will be deleted\nto save disk space and reduce clutter.",
            justify="center"
        ).pack(pady=10)
    
    def _add_deletion_pattern(self):
        """Add a new pattern entry for deletion."""
        var = tk.StringVar(value="")
        self.deletion_patterns_vars.append(var)
        
        # Find the patterns frame
        for child in self.settings_frame.winfo_children():
            if isinstance(child, ttk.Labelframe) and child.winfo_children() and \
               "Deletion Settings" in child.winfo_children()[0].cget("text"):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.Labelframe) and "Deletion Patterns" in subchild.cget("text"):
                        entry = ttk.Entry(subchild, textvariable=var)
                        entry.pack(fill="x", pady=2)
                        entry.focus_set()
                        break
    
    def _add_performance_settings(self):
        """Add performance settings section."""
        frame = self._add_section("Performance Settings")
        
        # Get performance settings from config
        performance = self.config.get("PERFORMANCE", {})
        
        # Thread count - ensure we're using a primitive integer value converted to string
        try:
            thread_count = int(performance.get('thread_count', 4))
        except (ValueError, TypeError):
            thread_count = 4
            
        self.performance_thread_count_var = tk.StringVar(value=str(thread_count))
        thread_frame = ttk.Frame(frame)
        thread_frame.pack(fill="x", pady=5)
        ttk.Label(thread_frame, text="Thread Count:").pack(side="left", padx=5)
        ttk.Entry(
            thread_frame,
            textvariable=self.performance_thread_count_var,
            width=5
        ).pack(side="left", padx=5)
        
        # Batch size - ensure we're using a primitive integer value converted to string
        try:
            batch_size = int(performance.get('batch_size', 100))
        except (ValueError, TypeError):
            batch_size = 100
            
        self.performance_batch_size_var = tk.StringVar(value=str(batch_size))
        batch_frame = ttk.Frame(frame)
        batch_frame.pack(fill="x", pady=5)
        ttk.Label(batch_frame, text="Batch Size:").pack(side="left", padx=5)
        ttk.Entry(
            batch_frame,
            textvariable=self.performance_batch_size_var,
            width=5
        ).pack(side="left", padx=5)
        
        # Help text
        ttk.Label(
            frame, 
            text="Higher thread count may improve performance on multi-core systems.\nLarger batch size can improve throughput but uses more memory.",
            justify="center",
            wraplength=400
        ).pack(pady=10)
    
    def _add_logging_settings(self):
        """Add logging settings section."""
        frame = self._add_section("Logging Settings")
        
        # Get logging settings from config
        logging_config = self.config.get("LOGGING", {})
        
        # Log level
        level_frame = ttk.Frame(frame)
        level_frame.pack(fill="x", pady=5)
        ttk.Label(level_frame, text="Log Level:").pack(side="left", padx=5)
        
        # Ensure we're using a primitive string value
        log_level = str(logging_config.get('level', 'INFO'))
        self.logging_level_var = tk.StringVar(value=log_level)
        level_combo = ttk.Combobox(
            level_frame,
            textvariable=self.logging_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            width=10,
            state="readonly"
        )
        level_combo.pack(side="left", padx=5)
        
        # File logging
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill="x", pady=5)
        
        # Ensure we're using a primitive boolean value
        file_enabled = bool(logging_config.get('file_enabled', True))
        self.logging_file_enabled_var = tk.BooleanVar(value=file_enabled)
        ttk.Checkbutton(
            file_frame,
            text="Enable File Logging",
            variable=self.logging_file_enabled_var
        ).pack(side="left", padx=5)
        
        # Log rotation
        rotation_frame = ttk.Frame(frame)
        rotation_frame.pack(fill="x", pady=5)
        
        # Ensure we're using a primitive boolean value
        rotation_enabled = bool(logging_config.get('rotation_enabled', True))
        self.logging_rotation_enabled_var = tk.BooleanVar(value=rotation_enabled)
        ttk.Checkbutton(
            rotation_frame,
            text="Enable Log Rotation",
            variable=self.logging_rotation_enabled_var
        ).pack(side="left", padx=5)
        
        # Max log size - ensure we're using a primitive integer value converted to string
        try:
            max_size = int(logging_config.get('max_size_mb', 10))
        except (ValueError, TypeError):
            max_size = 10
            
        self.logging_max_size_var = tk.StringVar(value=str(max_size))
        size_frame = ttk.Frame(frame)
        size_frame.pack(fill="x", pady=5)
        ttk.Label(size_frame, text="Max Log Size (MB):").pack(side="left", padx=5)
        ttk.Entry(
            size_frame,
            textvariable=self.logging_max_size_var,
            width=5
        ).pack(side="left", padx=5)
        
        # Backup count - ensure we're using a primitive integer value converted to string
        try:
            backup_count = int(logging_config.get('backup_count', 3))
        except (ValueError, TypeError):
            backup_count = 3
            
        self.logging_backup_count_var = tk.StringVar(value=str(backup_count))
        backup_frame = ttk.Frame(frame)
        backup_frame.pack(fill="x", pady=5)
        ttk.Label(backup_frame, text="Backup Count:").pack(side="left", padx=5)
        ttk.Entry(
            backup_frame,
            textvariable=self.logging_backup_count_var,
            width=5
        ).pack(side="left", padx=5)
    
    def _save_settings(self):
        """Save all settings to the configuration file."""
        try:
            # Texture quality settings removed as we're not processing textures
            
            # Update backup settings
            backup = self.config.get("BACKUP", {})
            backup.update({
                'enabled': self.backup_vars['enabled'].get(),
                'compression': self.backup_vars['compression'].get(),
                'max_backups': int(self.backup_vars['max_backups'].get()),
                'include_cfg': self.backup_vars['include_cfg'].get(),
                'include_materials': self.backup_vars['include_materials'].get()
            })
            self.config["BACKUP"] = backup
            
            # Update transparency settings
            transparency = self.config.get("TRANSPARENCY", {})
            transparency.update({
                'default_alpha': float(self.transparency_vars['default_alpha'].get()),
                'weapon_alpha': float(self.transparency_vars['weapon_alpha'].get()),
                'effect_alpha': float(self.transparency_vars['effect_alpha'].get()),
                'enable_fade': self.transparency_vars['enable_fade'].get()
            })
            self.config["TRANSPARENCY"] = transparency
            
            # Update weapon color settings
            weapon_colors = self.config.get("WEAPON_COLORS", {})
            for category, vars_dict in self.weapon_vars.items():
                if category in weapon_colors:
                    # Get non-empty patterns
                    patterns = [var.get() for var in vars_dict['patterns'] if var.get().strip()]
                    
                    weapon_colors[category].update({
                        'enabled': vars_dict['enabled'].get(),
                        'color': vars_dict['color'].get(),
                        'patterns': patterns
                    })
            self.config["WEAPON_COLORS"] = weapon_colors
            
            # Update C4 sound settings
            c4_sound = self.config.get("C4_SOUND_REPLACEMENT", {})
            # Get non-empty patterns
            patterns = [var.get() for var in self.c4_sound_patterns_vars if var.get().strip()]
            
            c4_sound.update({
                'enabled': self.c4_sound_enabled_var.get(),
                'preserve_paths': self.c4_sound_preserve_paths_var.get(),
                'sound_file': self.c4_sound_file_var.get(),
                'patterns': patterns
            })
            self.config["C4_SOUND_REPLACEMENT"] = c4_sound
            
            # Update prop shader settings
            prop_shader = self.config.get("PROP_SHADER", {})
            # Get non-empty patterns
            patterns = [var.get() for var in self.prop_shader_patterns_vars if var.get().strip()]
            
            prop_shader.update({
                'enabled': self.prop_shader_enabled_var.get(),
                'use_lightmapped': self.prop_shader_lightmapped_var.get(),
                'alpha': float(self.prop_shader_alpha_var.get()),
                'patterns': patterns
            })
            self.config["PROP_SHADER"] = prop_shader
            
            # Update deletion settings
            deletion = self.config.get("DELETION", {})
            # Get non-empty patterns
            patterns = [var.get() for var in self.deletion_patterns_vars if var.get().strip()]
            
            # Get category settings
            categories = deletion.get("categories", {})
            for category, data in self.deletion_categories.items():
                if category in categories:
                    categories[category]['enabled'] = data['enabled'].get()
            
            deletion.update({
                'enabled': self.deletion_enabled_var.get(),
                'patterns': patterns,
                'categories': categories
            })
            self.config["DELETION"] = deletion
            
            # Update performance settings
            performance = self.config.get("PERFORMANCE", {})
            performance.update({
                'thread_count': int(self.performance_thread_count_var.get()),
                'batch_size': int(self.performance_batch_size_var.get())
            })
            self.config["PERFORMANCE"] = performance
            
            # Update logging settings
            logging_config = self.config.get("LOGGING", {})
            logging_config.update({
                'level': self.logging_level_var.get(),
                'file_enabled': self.logging_file_enabled_var.get(),
                'rotation_enabled': self.logging_rotation_enabled_var.get(),
                'max_size_mb': int(self.logging_max_size_var.get()),
                'backup_count': int(self.logging_backup_count_var.get())
            })
            self.config["LOGGING"] = logging_config
            
            # Update module settings
            module_config = self.config.get("MODULES", {})
            
            # Get current values from the UI
            swep_detector_enabled = self.module_vars['swep_detector'].get()
            texture_extractor_enabled = self.module_vars['texture_extractor'].get()
            
            # Log the values being saved
            logging.info(f"Saving SWEP detector setting: {swep_detector_enabled}")
            logging.info(f"Saving Texture extractor setting: {texture_extractor_enabled}")
            
            # Create a new module config to ensure clean state
            module_config = {
                'swep_detector': swep_detector_enabled,
                'texture_extractor': texture_extractor_enabled
            }
            
            # Save to config
            self.config["MODULES"] = module_config
            logging.info(f"Updated module config: {self.config['MODULES']}")
            
            # Update update settings
            update_config = self.config.get("UPDATE", {})
            update_config.update({
                'enabled': self.update_vars['enabled'].get(),
                'auto_download': self.update_vars['auto_download'].get(),
                'include_beta': self.update_vars['include_beta'].get(),
                'backup_before_update': self.update_vars['backup_before_update'].get()
            })
            self.config["UPDATE"] = update_config
            
            # Force a deep copy of the config to ensure all changes are saved
            import copy
            config_to_save = copy.deepcopy(self.config)
            
            # Save all settings to file
            success = save_config(config_to_save)
            if success:
                save_settings_to_file()
                
                # Log the final config for debugging
                logging.info(f"Final module config saved: {config_to_save.get('MODULES', {})}")
                
                # Close dialog using our method to ensure cleanup
                self._on_dialog_close()
                messagebox.showinfo("Settings", "Settings saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save settings to file.")
            
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def _on_dialog_close(self):
        """Clean up resources and close the dialog."""
        try:
            # Unbind the mousewheel event to prevent errors after closing
            self.dialog.unbind_all("<MouseWheel>")
            self.dialog.destroy()
        except Exception as e:
            # In case of any errors during cleanup
            logging.error(f"Error closing settings dialog: {e}")
