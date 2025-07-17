import os
import yaml
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

def load_tools_config(config_dir: str = None) -> Dict[str, Any]:
    """
    Load tool configuration from multiple YAML files

    Args:
        config_dir: Directory containing config files. Defaults to current directory.

    Returns:
        Combined configuration dictionary
    """
    if config_dir is None:
        config_dir = Path(__file__).parent
    else:
        config_dir = Path(config_dir)

    # Load main config - try new name first, fall back to old name
    main_config_path = config_dir / "identity.yaml"

    with open(main_config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load tools from separate files
    tools_dir = config_dir / "tools"
    if not tools_dir.exists():
        print(f"Warning: Tools directory not found: {tools_dir}")
        return config

    all_tools = []

    # Load tools from each category file
    tool_files = [
        "desktop.yaml",
        "system.yaml",
        "gmail.yaml",
        "calendar.yaml",
        "conversation.yaml"
    ]

    for tool_file in tool_files:
        tool_path = tools_dir / tool_file
        if tool_path.exists():
            try:
                with open(tool_path, 'r') as f:
                    tool_config = yaml.safe_load(f)
                    if tool_config and 'tools' in tool_config:
                        all_tools.extend(tool_config['tools'])
                        print(f"Loaded {len(tool_config['tools'])} tools from {tool_file}")
            except Exception as e:
                print(f"Error loading {tool_file}: {e}")
        else:
            print(f"Warning: Tool file not found: {tool_path}")

    # Update config with loaded tools
    config['tools'] = all_tools

    # Replace dynamic placeholders in messages
    _replace_placeholders(config)

    print(f"Total tools loaded: {len(all_tools)}")
    return config

def get_tool_names(config: Dict[str, Any]) -> List[str]:
    """Get list of all tool names from config"""
    tool_names = []
    for tool in config.get('tools', []):
        if 'function' in tool and 'name' in tool['function']:
            tool_names.append(tool['function']['name'])
    return tool_names

def validate_tools_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate tool configuration and return any errors

    Returns:
        List of validation error messages
    """
    errors = []

    if 'tools' not in config:
        errors.append("No 'tools' key found in config")
        return errors

    tool_names = set()
    for i, tool in enumerate(config['tools']):
        if 'function' not in tool:
            errors.append(f"Tool {i}: Missing 'function' key")
            continue

        function = tool['function']
        if 'name' not in function:
            errors.append(f"Tool {i}: Missing 'name' in function")
            continue

        name = function['name']
        if name in tool_names:
            errors.append(f"Tool {i}: Duplicate tool name '{name}'")
        else:
            tool_names.add(name)

        if 'description' not in function:
            errors.append(f"Tool '{name}': Missing 'description'")

        if 'parameters' not in function:
            errors.append(f"Tool '{name}': Missing 'parameters'")

    return errors

def _replace_placeholders(config: Dict[str, Any]) -> None:
    """Replace dynamic placeholders in config messages"""
    # Get current date and time
    current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p %Z")
    
    # Get user name from local user_config.yaml
    full_name = "User"  # Fallback if config not found
    first_name = "User"
    try:
        config_dir = Path(__file__).parent
        user_config_path = config_dir / "user_config.yaml"
        if user_config_path.exists():
            with open(user_config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                full_name = user_config.get("user_name", full_name)
                # Extract first name for casual greeting
                first_name = full_name.split()[0] if full_name else first_name
    except Exception as e:
        print(f"Warning: Could not load user config: {e}")
    
    # Replace placeholders in messages
    if 'messages' in config:
        for message in config['messages']:
            if 'content' in message:
                message['content'] = message['content'].replace('{user_name}', full_name)
                message['content'] = message['content'].replace('{first_name}', first_name)
                message['content'] = message['content'].replace('{current_datetime}', current_datetime)

if __name__ == "__main__":
    # Test the loader
    try:
        config = load_tools_config()
        tool_names = get_tool_names(config)
        print(f"\nAvailable tools: {', '.join(tool_names)}")

        # Validate configuration
        errors = validate_tools_config(config)
        if errors:
            print(f"\nValidation errors:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\nConfiguration is valid!")

    except Exception as e:
        print(f"Error: {e}")
