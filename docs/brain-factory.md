# Brain Factory System

The Brain Factory is the central component responsible for AI backend selection, instantiation, and configuration management in SOFIA. It provides a unified interface for different AI providers while handling the complexities of backend switching and configuration loading.

## Overview

The Brain Factory implements the Factory design pattern to abstract the creation of brain instances. This allows SOFIA to seamlessly switch between different AI backends (Ollama, OpenAI) without requiring changes to the user interface or tool execution logic.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Brain Factory                            │
├─────────────────────────────────────────────────────────────┤
│  Configuration Loading                                      │
│  ┌─────────────────┐  ┌─────────────────┐                 │
│  │  sofia_config   │  │  tools.yaml     │                 │
│  │  .yaml          │  │  loading        │                 │
│  └─────────────────┘  └─────────────────┘                 │
├─────────────────────────────────────────────────────────────┤
│  Backend Selection Logic                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  if backend == 'openai':                               │ │
│  │      return OpenAIChatBrain(api_key, model)            │ │
│  │  else:                                                  │ │
│  │      return ChatBrain(chat_function)                   │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Brain Instance Creation                                    │
│  ┌─────────────────┐  ┌─────────────────┐                 │
│  │  OpenAI Brain   │  │  Ollama Brain   │                 │
│  │  (Cloud)        │  │  (Local)        │                 │
│  └─────────────────┘  └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

## Core Implementation

### File Location
`sofia/core/brain_factory.py`

### Key Functions

#### `create_brain(backend: Optional[str] = None) -> ChatBrain`

The main factory function that creates appropriate brain instances based on configuration.

```python
def create_brain(backend: Optional[str] = None) -> ChatBrain:
    \"\"\"
    Creates a brain instance based on configuration
    
    Args:
        backend: Optional backend override ('openai' or 'ollama')
        
    Returns:
        ChatBrain: Configured brain instance
        
    Raises:
        ValueError: If OpenAI backend selected but no API key available
    \"\"\"
    # Load configuration
    config = load_sofia_config()
    
    # Determine backend
    selected_backend = backend or config.get('ai_backend', 'ollama')
    
    if selected_backend.lower() == 'openai':
        # Load API key from environment
        api_key = load_env_file().get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(\"OpenAI API key not found in .env file\")
        
        # Get model configuration
        model = config.get('openai', {}).get('model', 'gpt-4o')
        
        return OpenAIChatBrain(api_key=api_key, model=model)
    else:
        # Default to Ollama
        from ollama import chat
        return ChatBrain(chat)
```

#### `get_brain_and_config() -> Tuple[ChatBrain, List[Dict], List[Dict]]`

Comprehensive function that loads both brain instance and configuration data.

```python
def get_brain_and_config():
    \"\"\"
    Load brain instance along with initial messages and tools
    
    Returns:
        Tuple containing:
        - ChatBrain: Configured brain instance
        - List[Dict]: Initial conversation messages
        - List[Dict]: Available tool specifications
    \"\"\"
    # Load tool configuration
    messages, tools = load_config()
    
    # Create brain instance
    brain = create_brain()
    
    return brain, messages, tools
```

#### `load_sofia_config() -> Dict[str, Any]`

Configuration file loader with fallback defaults.

```python
def load_sofia_config() -> Dict[str, Any]:
    \"\"\"
    Load SOFIA configuration from sofia_config.yaml
    
    Returns:
        Dict: Configuration settings with defaults
    \"\"\"
    config_path = Path('config/sofia_config.yaml')
    
    # Default configuration
    default_config = {
        'ai_backend': 'ollama',
        'openai': {
            'model': 'gpt-4o'
        },
        'ollama': {
            'model': 'sofia2'
        }
    }
    
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Merge with defaults
                return {**default_config, **config}
    except Exception as e:
        print(f\"Error loading config: {e}\")
    
    return default_config
```

#### `load_env_file(env_file: str = '.env') -> Dict[str, str]`

Environment file parser for API keys and secrets.

```python
def load_env_file(env_file: str = '.env') -> Dict[str, str]:
    \"\"\"
    Load environment variables from .env file
    
    Args:
        env_file: Path to environment file
        
    Returns:
        Dict: Environment variables as key-value pairs
    \"\"\"
    env_vars = {}
    
    if not os.path.exists(env_file):
        return env_vars
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip().strip('\"').strip(\"'\")
                env_vars[key.strip()] = value
    
    return env_vars
```

## Configuration Management

### Backend Selection Priority

1. **Function Parameter**: Direct backend specification
2. **Configuration File**: `sofia_config.yaml` setting
3. **Default**: Falls back to 'ollama'

### Configuration Files

#### `config/sofia_config.yaml`
```yaml
# AI Backend Selection
ai_backend: openai  # or 'ollama'

# OpenAI Configuration
openai:
  model: gpt-4o

# Ollama Configuration  
ollama:
  model: sofia2
```

#### `.env` (API Keys)
```bash
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Other API keys as needed
```

#### `config/tools.yaml` (Tools Configuration)
```yaml
messages:
  - role: system
    content: "System prompt with {USER_NAME} placeholder"
  - role: assistant
    content: "Hi! How can I help you today?"

tools:
  - type: function
    function:
      name: example_tool
      description: "Tool description"
      parameters:
        # OpenAPI schema
```

## Backend-Specific Initialization

### OpenAI Brain Initialization

```python
# Configuration validation
if selected_backend.lower() == 'openai':
    api_key = load_env_file().get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError(
            \"OpenAI API key not found. Please set OPENAI_API_KEY in .env file\"
        )
    
    model = config.get('openai', {}).get('model', 'gpt-4o')
    return OpenAIChatBrain(api_key=api_key, model=model)
```

### Ollama Brain Initialization

```python
# Simple local initialization
else:
    from ollama import chat
    return ChatBrain(chat)
```

## Error Handling

### Configuration Errors

```python
try:
    config = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f\"Error parsing config file: {e}\")
    return default_config
except FileNotFoundError:
    print(\"Config file not found, using defaults\")
    return default_config
```

### API Key Validation

```python
def validate_openai_config():
    \"\"\"Validate OpenAI configuration before brain creation\"\"\"
    env_vars = load_env_file()
    api_key = env_vars.get('OPENAI_API_KEY')
    
    if not api_key:
        raise ValueError(
            \"OpenAI API key not found. Please:\\n\"
            \"1. Create .env file from .env.template\\n\"
            \"2. Add your OpenAI API key\\n\"
            \"3. Restart the application\"
        )
    
    if api_key == 'your_openai_api_key_here':
        raise ValueError(\"Please replace template API key with your actual key\")
    
    return api_key
```

## Usage Examples

### Basic Brain Creation

```python
from sofia.core.brain_factory import create_brain

# Use configured backend
brain = create_brain()

# Force specific backend
openai_brain = create_brain('openai')
ollama_brain = create_brain('ollama')
```

### Complete Setup

```python
from sofia.core.brain_factory import get_brain_and_config

# Get everything needed for a chat session
brain, initial_messages, tools = get_brain_and_config()

# Start conversation
messages = initial_messages.copy()
user_input = \"Hello, SOFIA!\"
messages.append({\"role\": \"user\", \"content\": user_input})

# Process with appropriate brain
if hasattr(brain, 'continuous_chat'):
    # Ollama brain
    response, _ = brain.continuous_chat(messages, tools)
else:
    # OpenAI brain  
    response, _ = brain.continuous_chat(messages, tools, stream=True)
```

### Configuration Management

```python
from sofia.core.brain_factory import load_sofia_config

# Load current configuration
config = load_sofia_config()
current_backend = config.get('ai_backend')

# Switch backend
config['ai_backend'] = 'openai'
with open('config/sofia_config.yaml', 'w') as f:
    yaml.dump(config, f)

# Create new brain with updated config
new_brain = create_brain()
```

## Integration Points

### Desktop Application

```python
# sofia/ui/desktop/main.py
from sofia.core.brain_factory import get_brain_and_config

class ChatWindow:
    def __init__(self):
        self.brain, self.messages, self.tools = get_brain_and_config()
        # Rest of initialization
```

### Web Application

```python
# sofia/ui/web/gradio_app.py
def create_demo():
    global brain, messages, tools
    brain, messages, tools = get_brain_and_config()
    # Create Gradio interface
```

### Backend Switching Utility

```python
# switch_backend.py
from sofia.core.brain_factory import load_sofia_config

def switch_to_openai():
    config = load_sofia_config()
    config['ai_backend'] = 'openai'
    save_config(config)
    print(\"Switched to OpenAI backend\")

def switch_to_ollama():
    config = load_sofia_config()
    config['ai_backend'] = 'ollama'
    save_config(config)
    print(\"Switched to Ollama backend\")
```

## Extensibility

### Adding New Backends

1. **Create Brain Class**: Implement the same interface as existing brains
2. **Update Factory**: Add new backend logic to `create_brain()`
3. **Add Configuration**: Update `sofia_config.yaml` schema
4. **Update Documentation**: Add setup instructions

Example new backend:

```python
def create_brain(backend: Optional[str] = None) -> ChatBrain:
    # ... existing code ...
    
    elif selected_backend.lower() == 'anthropic':
        api_key = load_env_file().get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(\"Anthropic API key not found\")
        return AnthropicChatBrain(api_key=api_key)
```

### Custom Configuration Sources

```python
def load_config_from_database():
    \"\"\"Example: Load configuration from database instead of file\"\"\"
    # Database connection and query logic
    pass

def create_brain_with_custom_config():
    \"\"\"Create brain with custom configuration source\"\"\"
    config = load_config_from_database()
    # Rest of brain creation logic
```

## Testing

### Unit Tests

```python
def test_brain_creation():
    \"\"\"Test basic brain creation\"\"\"
    brain = create_brain('ollama')
    assert isinstance(brain, ChatBrain)

def test_config_loading():
    \"\"\"Test configuration loading\"\"\"
    config = load_sofia_config()
    assert 'ai_backend' in config

def test_env_file_parsing():
    \"\"\"Test environment file parsing\"\"\"
    env_vars = load_env_file('test.env')
    assert isinstance(env_vars, dict)
```

### Integration Tests

```python
def test_complete_setup():
    \"\"\"Test complete brain and config loading\"\"\"
    brain, messages, tools = get_brain_and_config()
    assert brain is not None
    assert len(messages) > 0
    assert len(tools) > 0
```

The Brain Factory system provides a robust, extensible foundation for managing AI backends in SOFIA while maintaining clean separation of concerns and easy configuration management.