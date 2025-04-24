"""
Configuration Manager for Texture Extractor
Handles loading, saving, and accessing configuration settings
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Default configuration values
DEFAULT_CONFIG = {
    # Core Features
    "SKIP_DEPENDENCIES": False,
    "ENABLE_WEAPON_COLORS": True,
    "ENABLE_TRANSPARENCY": True,
    "ENABLE_CUSTOM_SOUNDS": True,
    
    # Module Settings
    "MODULES": {
        "swep_detector": True,  # Enable/disable SWEP detection module
        "texture_extractor": True  # Enable/disable texture extraction module
    },
    
    # Processing Options
    "ENABLE_PARALLEL_PROCESSING": True,
    "MAX_THREADS": 4,
    "ENABLE_MEMORY_OPTIMIZATION": True,
    "CHUNK_SIZE": 1024 * 1024,  # 1MB
    
    # Texture Quality settings removed as we're not processing textures
    
    # Performance Settings
    "PERFORMANCE": {
        "cache_enabled": True,
        "cache_size": 512,
        "preload_textures": True,
        "batch_processing": True,
        "batch_size": 100
    },
    
    # Backup Settings
    "BACKUP": {
        "enabled": True,
        "location": None,
        "max_backups": 5,
        "compression": True,
        "include_cfg": True,
        "include_materials": True
    },
    
    # Transparency Settings
    "TRANSPARENCY": {
        "default_alpha": 0.45,
        "weapon_alpha": 1.0,
        "effect_alpha": 0.5,
        "prop_alpha": 0.75,
        "enable_fade": True,
        "fade_start": 500,
        "fade_end": 1000
    },
    
    # C4 Sound Replacement Settings
    "C4_SOUND_REPLACEMENT": {
        "enabled": True,
        "preserve_paths": True,
        "sound_file": "npc/zombie/zombie_pain1.wav",
        "patterns": [
            "weapons/c4",
            "player/c4",
            "items/c4"
        ]
    },
    
    # Prop Shader Settings
    "PROP_SHADER": {
        "enabled": True,
        "use_lightmapped": True,
        "alpha": 0.9,
        "patterns": [
            "/props/", 
            "models/props", 
            "/prop_", 
            "prop_"
        ]
    },
    
    # Skip Patterns
    "SKIP_PATTERNS": {
        "enabled": True,
        "patterns": {
            "props": {
                "enabled": True,
                "patterns": [
                    "/props/", 
                    "models/props",
                    "/prop_"
                ]
            },
            "ui": {
                "enabled": True,
                "patterns": [
                    "/ui/",
                    "vgui/",
                    "hud/"
                ]
            },
            "sprites": {
                "enabled": True,
                "patterns": [
                    "/sprites/",
                    "sprites/",
                    "effects/sprites",
                    "effects/light",
                    "effects/flare",
                    "effects/glow",
                    "effects/flashlight",
                    "effects/lamp",
                    "particle/",
                    "particles/"
                ]
            }
        }
    },
    
    # Sound Settings
    "SOUND": {
        "enable_custom_sounds": True,
        "c4_sounds": {
            "plant": {
                "enabled": True,
                "sound_type": "scream",
                "custom_path": None,
                "volume": "1.0",
                "pitch": "100"
            },
            "beep": {
                "enabled": True,
                "sound_type": "scream",
                "custom_path": None,
                "volume": "1.0",
                "pitch": "100"
            },
            "explode": {
                "enabled": True,
                "sound_type": "scream",
                "custom_path": None,
                "volume": "1.0",
                "pitch": "100"
            }
        },
        "sound_types": {
            "scream": {
                "male01": "vo/npc/male01/pain07.wav",
                "male02": "vo/npc/male01/pain08.wav",
                "female01": "vo/npc/female01/pain07.wav",
                "zombie": "npc/zombie/zombie_pain6.wav",
                "headcrab": "npc/headcrab/pain1.wav",
                "combine": "npc/combine_soldier/pain3.wav"
            },
            "beep": {
                "normal": "buttons/button17.wav",
                "danger": "buttons/blip1.wav",
                "warning": "buttons/blip2.wav"
            },
            "custom": {}
        },
        "backup_original_sounds": True,
        "restore_on_exit": False
    },
    
    # Workshop Integration
    "WORKSHOP": {
        "process_workshop": True,
        "auto_update": True,
        "download_missing": True,
        "verify_files": True,
        "max_workshop_size": 2048,
        "workshop_cache": True
    },
    
    # Auto-Update Settings
    "UPDATE": {
        "enabled": True,
        "check_interval": 86400,  # Check once per day (in seconds)
        "auto_download": True,
        "notify_only": False,
        "include_beta": False,
        "backup_before_update": True,
        "update_channel": "stable",
        "last_check": 0,
        "skip_versions": []
    },
    
    # Logging and Debug
    "LOGGING": {
        "log_level": "INFO",
        "log_to_file": True,
        "log_format": "detailed",
        "max_log_size": 10,
        "max_log_files": 5,
        "log_location": None
    },
    
    # GUI Settings
    "GUI": {
        "enable_gui": True,
        "theme": "default",
        "show_preview": True,
        "window_size": "800x600",
        "font_size": 10
    },
    
    # Weapon Colors
    "WEAPON_COLORS": {
        "pistol": {
            "enabled": True,
            "color": "[1 0 0]",
            "name": "Red",
            "patterns": [
                "pistol", "glock", "usp", "deagle", "revolver", "357", "p228", "p250", "magnum", "fiveseven", "elite"
            ]
        },
        "rifle": {
            "enabled": True,
            "color": "[0 1 0]",
            "name": "Green",
            "patterns": [
                "rifle", "ak47", "m4a1", "famas", "galil", "aug", "sg552", "awp", "scout", "sniper", "assault", "carbine"
            ]
        },
        "smg": {
            "enabled": True,
            "color": "[0 0 1]",
            "name": "Blue",
            "patterns": [
                "smg", "mp5", "mp7", "mac10", "ump45", "p90", "tmp", "mp5navy"
            ]
        },
        "shotgun": {
            "enabled": True,
            "color": "[1 0 1]",
            "name": "Purple",
            "patterns": [
                "shotgun", "nova", "mag7", "sawedoff", "xm1014", "spas", "pump", "m3", "autoshotgun", "pumpshotgun"
            ]
        },
        "crossbow": {
            "enabled": True,
            "color": "[1 0.5 0.5]",
            "name": "Pink",
            "patterns": [
                "crossbow", "bow", "arrow"
            ]
        },
        "explosive": {
            "enabled": True,
            "color": "[1 0.5 0]",
            "name": "Orange",
            "patterns": [
                "grenade", "explosive", "c4", "rpg", "missile", "bomb", "mine", "dynamite", "tnt", "frag", "slam"
            ]
        },
        "medical": {
            "enabled": True,
            "color": "[0 1 1]",
            "name": "Cyan",
            "patterns": [
                "medkit", "defibrillator", "health", "heal", "bandage", "first_aid", "pain_pills", "adrenaline"
            ]
        },
        "utility": {
            "enabled": True,
            "color": "[1 1 0]",
            "name": "Yellow",
            "patterns": [
                "tool", "camera", "keys", "lockpick", "keypad", "atm", "card", "checker", "pocket"
            ]
        },
        "special": {
            "enabled": True,
            "color": "[0 1 1]",
            "name": "Cyan",
            "patterns": [
                "gravity", "physcannon", "physgun", "toolgun", "tool", "stunstick", "stun", "taser", "crowbar", "bat"
            ]
        }
    },
    
    # Delete Patterns
    "DELETE_PATTERNS": {
        "enabled": True,
        "categories": {
            "trees": {
                "enabled": True,
                "patterns": [
                    "/tree", "/trees", "foliage/", "nature/trees", "nature/tree",
                    "props/tree", "props/foliage", "nature/bush", "nature/plant",
                    "props/plant", "props/bush", "props/grass", "nature/grass"
                ]
            },
            "effects": {
                "enabled": True,
                "patterns": [
                    "effects/sprites", "effects/light", "effects/flare",
                    "effects/glow", "effects/flashlight", "effects/lamp",
                    "particle/", "particles/", "/sprites/", "sprites/"
                ]
            },
            "ui": {
                "enabled": True,
                "patterns": [
                    "/ui/", "vgui/", "hud/", "overlay/",
                    "menu/", "/menu/", "scoreboard/", "/scoreboard/"
                ]
            },
            "hands": {
                "enabled": True,
                "patterns": [
                    "/hands/", "hands/", "arms/", "/arms/"
                ]
            },
            "props": {
                "enabled": True,
                "patterns": [
                    "/props/", "models/props", "/prop_",
                    "furniture/", "/furniture/"
                ]
            }
        }
    }
}

def get_config_path():
    """Get the path to the configuration file."""
    # Use user's home directory for configuration
    home_dir = Path.home()
    config_dir = home_dir / ".texture_extractor"
    
    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    return config_dir / "config.json"

def load_config():
    """Load configuration from file or create default if not exists."""
    config_path = get_config_path()
    
    # If config file exists, load it
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logging.info(f"Configuration loaded from {config_path}")
                return config
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            logging.info("Using default configuration")
            return DEFAULT_CONFIG
    else:
        # Create default config
        save_config(DEFAULT_CONFIG)
        logging.info(f"Default configuration created at {config_path}")
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file."""
    config_path = get_config_path()
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        logging.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        return False

def save_settings_to_file():
    """Save current settings to a timestamped file in the logs directory."""
    try:
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Create timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        settings_file = log_dir / f"settings_{timestamp}.json"
        
        # Get current configuration
        config = load_config()
        
        # Save to file
        with open(settings_file, 'w') as f:
            json.dump(config, f, indent=4)
            
        logging.info(f"Settings saved to {settings_file}")
        return True
    except Exception as e:
        logging.error(f"Error saving settings to file: {e}")
        return False
