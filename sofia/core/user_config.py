"""
User Configuration Management
Handles loading and accessing user-specific configuration
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

def get_user_config_path() -> Path:
    """Get the path to user configuration file"""
    return Path.home() / "SOFIA" / "config" / "user_config.yaml"

def load_user_config() -> Dict[str, Any]:
    """Load user configuration from file"""
    config_path = get_user_config_path()
    
    if not config_path.exists():
        # Return default configuration if file doesn't exist
        return {
            "user_name": "User",
            "email": "",
            "display_name": "User"
        }
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading user config: {e}")
        return {
            "user_name": "User", 
            "email": "",
            "display_name": "User"
        }

def get_user_name() -> str:
    """Get the user's name from configuration"""
    config = load_user_config()
    return config.get("user_name", "User")

def get_user_email() -> str:
    """Get the user's email from configuration"""
    config = load_user_config()
    return config.get("email", "")

def get_display_name() -> str:
    """Get the user's display name for emails"""
    config = load_user_config()
    return config.get("display_name", config.get("user_name", "User"))

def update_user_config(updates: Dict[str, Any]) -> bool:
    """Update user configuration with new values"""
    try:
        config = load_user_config()
        config.update(updates)
        
        config_path = get_user_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return True
    except Exception as e:
        print(f"Error updating user config: {e}")
        return False