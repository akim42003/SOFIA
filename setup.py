#!/usr/bin/env python3
"""
SOFIA Setup Script
Configures user-specific settings for the SOFIA AI assistant
"""

import os
import yaml
import json
from pathlib import Path

def get_user_config():
    """Collect user configuration information"""
    print("=== SOFIA Setup ===")
    print("Welcome to SOFIA! Let's configure your personal settings.\n")
    
    # Get user information
    user_name = input("Enter your full name (e.g., 'John Doe'): ").strip()
    if not user_name:
        user_name = "User"
    
    email = input("Enter your email address (optional, for Gmail integration): ").strip()
    
    # Get preferred display name for emails
    display_name = input(f"Enter your display name for emails (default: '{user_name}'): ").strip()
    if not display_name:
        display_name = user_name
    
    return {
        "user_name": user_name,
        "email": email,
        "display_name": display_name
    }

def create_user_config_file(config_data):
    """Create user configuration file"""
    config_dir = Path.home() / "SOFIA" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = config_dir / "user_config.yaml"
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    print(f"User configuration saved to: {config_file}")
    return config_file

def update_tools_config(user_config):
    """Update tools.yaml with user-specific information"""
    tools_file = Path.home() / "SOFIA" / "config" / "tools.yaml"
    
    if tools_file.exists():
        with open(tools_file, 'r') as f:
            tools_config = yaml.safe_load(f)
        
        # Update system message with user's name
        for message in tools_config.get('messages', []):
            if message.get('role') == 'system':
                content = message.get('content', '')
                # Replace placeholder with actual user name
                content = content.replace('{USER_NAME}', user_config["user_name"])
                message['content'] = content
        
        # Update email tool description
        for tool in tools_config.get('tools', []):
            if tool.get('function', {}).get('name') == 'gmail_send_emails':
                func = tool['function']
                # Update description
                func['description'] = func['description'].replace('{DISPLAY_NAME}', user_config["display_name"])
                # Update parameter example
                for prop_name, prop_data in func.get('parameters', {}).get('properties', {}).items():
                    if prop_name == 'sender_name':
                        prop_data['description'] = prop_data['description'].replace('{DISPLAY_NAME}', user_config["display_name"])
        
        # Save updated config
        with open(tools_file, 'w') as f:
            yaml.dump(tools_config, f, default_flow_style=False)
        
        print(f"Updated tools configuration with your name: {user_config['user_name']}")

def update_modelfiles(user_config):
    """Update Modelfiles with user-specific information"""
    # Update enhanced Modelfile
    modelfile_enhanced_path = Path.home() / "SOFIA" / "config" / "Modelfile.enhanced"
    if modelfile_enhanced_path.exists():
        with open(modelfile_enhanced_path, 'r') as f:
            content = f.read()
        content = content.replace('{USER_NAME}', user_config["user_name"])
        with open(modelfile_enhanced_path, 'w') as f:
            f.write(content)
        print(f"Updated Modelfile.enhanced with your name: {user_config['user_name']}")
    
    # Update regular Modelfile
    modelfile_path = Path.home() / "SOFIA" / "config" / "Modelfile"
    if modelfile_path.exists():
        with open(modelfile_path, 'r') as f:
            content = f.read()
        content = content.replace('{USER_NAME}', user_config["user_name"])
        with open(modelfile_path, 'w') as f:
            f.write(content)
        print(f"Updated Modelfile with your name: {user_config['user_name']}")

def create_env_template():
    """Create .env template file"""
    env_template = Path.home() / "SOFIA" / ".env.template"
    
    template_content = """# SOFIA Environment Configuration
# Copy this file to .env and fill in your API keys

# OpenAI API Key (required for OpenAI backend)
OPENAI_API_KEY=your_openai_api_key_here

# Other API keys can be added here as needed
"""
    
    with open(env_template, 'w') as f:
        f.write(template_content)
    
    print(f"Created .env template at: {env_template}")
    print("Remember to copy .env.template to .env and add your API keys!")

def main():
    """Main setup function"""
    try:
        # Get user configuration
        user_config = get_user_config()
        
        # Create user config file
        config_file = create_user_config_file(user_config)
        
        # Update tools and modelfile configurations
        update_tools_config(user_config)
        update_modelfiles(user_config)
        
        # Create .env template
        create_env_template()
        
        print("\n=== Setup Complete! ===")
        print(f"✓ User configuration saved")
        print(f"✓ Tools configuration updated")
        print(f"✓ Modelfiles updated")
        print(f"✓ Environment template created")
        print(f"\nYour SOFIA assistant is now configured for: {user_config['user_name']}")
        print(f"SOFIA directory: {Path.home() / 'SOFIA'}")
        
        print("\nNext steps:")
        print("1. Copy .env.template to .env and add your API keys")
        print("2. Run 'python -m sofia.ui.web.gradio_app' to start the web interface")
        print("3. Or run 'python -m sofia.ui.desktop.main' for the desktop app")
        
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
    except Exception as e:
        print(f"Error during setup: {e}")

if __name__ == "__main__":
    main()