#!/usr/bin/env python3
"""
Script to switch between Ollama (local) and OpenAI (cloud) backends for SOFIA
"""
import os
import sys
import yaml
from pathlib import Path


def load_env_file(env_file='.env'):
    """Load environment variables from .env file"""
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value
    return env_vars


def load_config(config_file='config/sofia_config.yaml'):
    """Load current configuration"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    else:
        return {
            'ai_backend': 'ollama',
            'ollama': {'model': 'sofia2'},
            'openai': {'model': 'gpt-4o-mini'}
        }


def save_config(config, config_file='config/sofia_config.yaml'):
    """Save configuration"""
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def check_openai_key():
    """Check if OpenAI API key is available"""
    # Check in order: config file, .env file, environment variable
    config = load_config()
    
    # 1. Check config file
    api_key = config.get('openai', {}).get('api_key')
    if api_key:
        return True
    
    # 2. Check .env file
    env_vars = load_env_file()
    if env_vars.get('OPENAI_API_KEY'):
        return True
    
    # 3. Check environment variable
    if os.getenv('OPENAI_API_KEY'):
        return True
    
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python switch_backend.py [ollama|openai|status]")
        print("\nCommands:")
        print("  ollama  - Switch to local Ollama backend")
        print("  openai  - Switch to OpenAI cloud backend")
        print("  status  - Show current backend configuration")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    config = load_config()
    
    if command == 'status':
        current_backend = config.get('ai_backend', 'ollama')
        print(f"Current backend: {current_backend}")
        
        if current_backend == 'openai':
            model = config.get('openai', {}).get('model', 'gpt-4o-mini')
            print(f"OpenAI model: {model}")
            
            if check_openai_key():
                print("OpenAI API key: ✓ Found")
                # Show where the key was found
                env_vars = load_env_file()
                if config.get('openai', {}).get('api_key'):
                    print("  Source: config/sofia_config.yaml")
                elif env_vars.get('OPENAI_API_KEY'):
                    print("  Source: .env file")
                elif os.getenv('OPENAI_API_KEY'):
                    print("  Source: environment variable")
            else:
                print("OpenAI API key: ✗ Not found")
                print("\nTo set OpenAI API key:")
                print("1. Create a .env file with: OPENAI_API_KEY=your-key-here")
                print("2. Or add to config/sofia_config.yaml under openai.api_key")
                print("3. Or set environment variable: export OPENAI_API_KEY='your-key'")
        else:
            model = config.get('ollama', {}).get('model', 'sofia2')
            print(f"Ollama model: {model}")
    
    elif command == 'ollama':
        config['ai_backend'] = 'ollama'
        save_config(config)
        print("✓ Switched to Ollama (local) backend")
        print(f"Using model: {config.get('ollama', {}).get('model', 'sofia2')}")
    
    elif command == 'openai':
        if not check_openai_key():
            print("✗ OpenAI API key not found!")
            print("\nTo use OpenAI backend, you need to set your API key:")
            print("1. Create a .env file in the project root with:")
            print("   OPENAI_API_KEY=your-key-here")
            print("2. Or add to config/sofia_config.yaml:")
            print("   openai:")
            print("     api_key: 'your-key-here'")
            print("3. Or set environment variable: export OPENAI_API_KEY='your-key'")
            sys.exit(1)
        
        config['ai_backend'] = 'openai'
        save_config(config)
        print("✓ Switched to OpenAI (cloud) backend")
        print(f"Using model: {config.get('openai', {}).get('model', 'gpt-4o-mini')}")
        print("\nNote: OpenAI API usage will incur costs based on your usage.")
    
    else:
        print(f"Unknown command: {command}")
        print("Use: python switch_backend.py [ollama|openai|status]")
        sys.exit(1)


if __name__ == "__main__":
    main()