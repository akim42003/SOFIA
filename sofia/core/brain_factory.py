"""
Brain Factory - Creates appropriate AI brain based on configuration
"""
import os
import yaml
from typing import Optional, Tuple, List, Dict
from sofia.core.brain import ChatBrain, load_config
from sofia.core.openai_brain import OpenAIChatBrain
from ollama import chat


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


def load_sofia_config(config_file='config/sofia_config.yaml'):
    """Load SOFIA configuration"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    else:
        # Default configuration
        return {
            'ai_backend': 'ollama',
            'ollama': {'model': 'sofia2'},
            'openai': {'model': 'gpt-4o'}
        }


def create_brain(backend: Optional[str] = None) -> ChatBrain:
    """
    Create appropriate brain instance based on configuration
    
    Args:
        backend: Override backend selection ('ollama' or 'openai')
        
    Returns:
        ChatBrain or OpenAIChatBrain instance
    """
    config = load_sofia_config()
    
    # Use provided backend or get from config
    selected_backend = backend or config.get('ai_backend', 'ollama')
    
    if selected_backend.lower() == 'openai':
        # Create OpenAI brain
        openai_config = config.get('openai', {})
        
        # Try to get API key from multiple sources
        api_key = openai_config.get('api_key')
        if not api_key:
            # Try .env file
            env_vars = load_env_file()
            api_key = env_vars.get('OPENAI_API_KEY')
        if not api_key:
            # Try environment variable
            api_key = os.getenv('OPENAI_API_KEY')
            
        model = openai_config.get('model', 'gpt-4o')
        
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set it in:\n"
                "1. .env file: OPENAI_API_KEY=your-key\n"
                "2. config/sofia_config.yaml under openai.api_key\n"
                "3. Environment variable: export OPENAI_API_KEY='your-key'"
            )
        
        return OpenAIChatBrain(api_key=api_key, model=model)
    else:
        # Create Ollama brain (default)
        return ChatBrain(chat)


def get_brain_and_config(backend: Optional[str] = None) -> Tuple[ChatBrain, List[Dict], List[Dict]]:
    """
    Get brain instance along with messages and tools configuration
    
    Args:
        backend: Override backend selection ('ollama' or 'openai')
        
    Returns:
        Tuple of (brain_instance, messages, tools)
    """
    brain = create_brain(backend)
    messages, tools = load_config()
    return brain, messages, tools