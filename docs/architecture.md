# SOFIA Architecture Overview

SOFIA is a modular AI assistant system designed with flexibility, extensibility, and user-agnosticism in mind. This document details the complete system architecture.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         SOFIA System                           │
├─────────────────────────────────────────────────────────────────┤
│  User Interfaces                                               │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Desktop App    │  │   Web App       │                     │
│  │  (PyQt6)        │  │  (Gradio)       │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Core Brain System                                             │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Brain Factory  │  │  Message        │                     │
│  │  (Selection)    │  │  Conversion     │                     │
│  └─────────────────┘  └─────────────────┘                     │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Ollama Brain   │  │  OpenAI Brain   │                     │
│  │  (Local)        │  │  (Cloud)        │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Tools & Integrations                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Desktop Tools  │  │  System Tools   │  │  Gmail Tools    │ │
│  │  (Automation)   │  │  (File/Command) │  │  (Email)        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐                                           │
│  │  Vision Tools   │                                           │
│  │  (OmniParser)   │                                           │
│  └─────────────────┘                                           │
├─────────────────────────────────────────────────────────────────┤
│  Configuration & Storage                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  User Config    │  │  Tools Config   │  │  Environment    │ │
│  │  (Personal)     │  │  (Functions)    │  │  (API Keys)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. User Interfaces Layer

#### Desktop Application (`sofia/ui/desktop/`)
- **Framework**: PyQt6
- **Main Components**:
  - `main.py` - Application entry point
  - `chat_window.py` - Main chat interface
  - `analysis_thread.py` - Background AI processing
- **Features**:
  - Real-time streaming responses
  - Image drag-and-drop support
  - System tray integration
  - Offline operation support

#### Web Application (`sofia/ui/web/`)
- **Framework**: Gradio
- **Main Components**:
  - `gradio_app.py` - Web interface implementation
- **Features**:
  - Browser-based access
  - Multimodal input support
  - Real-time tool execution feedback
  - Cross-platform compatibility

### 2. Brain System Layer

#### Brain Factory (`sofia/core/brain_factory.py`)
- **Purpose**: Backend selection and instantiation
- **Key Functions**:
  - `create_brain()` - Create method for brain instances
  - `get_brain_and_config()` - Configuration loading
  - `load_sofia_config()` - Settings management
- **Logic**: Determines appropriate brain based on configuration

#### Ollama Brain (`sofia/core/brain.py`)
- **Purpose**: Local AI model integration
- **Key Features**:
  - Local model execution
  - Streaming response support
  - Tool call execution
  - Memory management
- **Model Support**: Any Ollama-compatible model

#### OpenAI Brain (`sofia/core/openai_brain.py`)
- **Purpose**: Cloud AI service integration
- **Key Features**:
  - OpenAI API integration
  - Message format conversion
  - Vision API support
  - Error handling and retries
- **Models**: GPT-4o, GPT-4, GPT-3.5-turbo

### 3. Tools & Integrations Layer

#### Desktop Tools (`sofia/core/tools/desktop.py`)
- **Purpose**: Desktop automation and screen interaction
- **Functions**:
  - `take_screenshot()` - Screen capture
  - `move_mouse()` - Mouse positioning
  - `click_mouse()` - Mouse interaction
  - `type_text()` - Keyboard input
  - `press_key()` - Key combinations
  - `hotkey()` - Keyboard shortcuts
- **Dependencies**: PyAutoGUI, Pillow

#### System Tools (`sofia/core/tools/system.py`)
- **Purpose**: File operations and command execution
- **Functions**:
  - `save_file()` - File writing with path normalization
  - `read_file()` - File reading with error handling
  - `execute_command()` - Shell command execution
  - `normalize_path()` - Path sandboxing
- **Security**: All operations scoped to `~/SOFIA/`

#### Gmail Integration (`sofia/integrations/gmail/`)
- **Purpose**: Email management and automation
- **Components**:
  - `client.py` - Gmail API wrapper
  - OAuth2 authentication
  - Message parsing and formatting
- **Functions**:
  - `gmail_search_emails()` - Search functionality
  - `fetch_gmail()` - Message retrieval
  - `send_gmail()` - Email composition and sending

#### Vision Processing (`sofia/vision/`)
- **Purpose**: Image analysis and UI understanding
- **Components**:
  - `omniparser.py` - OmniParser integration
  - Screenshot analysis
  - UI element detection
- **Capabilities**:
  - Text extraction from images
  - UI element identification
  - Visual content description

### 4. Configuration & Storage Layer

#### User Configuration (`sofia/core/user_config.py`)
- **Purpose**: Personal settings management
- **Storage**: `~/SOFIA/config/user_config.yaml`
- **Settings**:
  - User name and display name
  - Email preferences
  - Personalization options
- **Functions**:
  - `load_user_config()` - Settings loading
  - `update_user_config()` - Settings modification

#### Tools Configuration (`config/tools.yaml`)
- **Purpose**: Function definitions and system prompts
- **Structure**:
  - `messages` - System prompt templates
  - `tools` - Function specifications
- **Features**:
  - OpenAPI-compatible schemas
  - Parameter validation
  - User-customizable prompts

#### Environment Configuration
- **Files**:
  - `.env` - API keys and secrets
  - `.env.template` - Configuration template
  - `sofia_config.yaml` - Backend selection
- **Security**: Secrets excluded from version control

## Data Flow

### 1. User Input Processing
```
User Input → UI Layer → Brain Factory → Selected Brain → Tools → Response
```

### 2. Tool Execution Flow
```
Tool Call → Parameter Validation → Function Execution → Result Processing → Response Integration
```

### 3. Message Processing
```
Raw Message → Format Conversion → Context Addition → AI Processing → Response Generation
```

## Security Architecture

### 1. Path Sandboxing
- All file operations restricted to `~/SOFIA/`
- Path normalization prevents directory traversal
- Automatic path validation and correction

### 2. API Key Management
- Environment variable storage
- Template-based configuration
- No secrets in version control

### 3. Tool Execution Safety
- Parameter validation
- Error handling and recovery
- Execution timeout protection

## Extensibility Points

### 1. Custom Tools
- Add new functions to tools configuration
- Implement function in appropriate module
- Register in brain's `available_functions`

### 2. New AI Backends
- Implement brain interface
- Add to brain factory
- Update configuration options

### 3. Additional UIs
- Implement core message processing
- Handle tool execution lifecycle
- Integrate with brain factory

## Performance Considerations

### 1. Streaming Responses
- Real-time token delivery
- Chunked processing
- Memory-efficient handling

### 2. Concurrent Tool Execution
- Parallel function calls
- Background processing
- Non-blocking UI updates

### 3. Resource Management
- Image processing optimization
- Memory usage monitoring
- Connection pooling

## Configuration Management

### 1. User Setup Process
```
setup.py → User Input → Config Generation → File Updates → Validation
```

### 2. Runtime Configuration
- Dynamic backend switching
- Hot-reload capability
- Environment variable overrides

### 3. Deployment Flexibility
- Multi-user support
- Containerization ready
- Cloud deployment compatible

## Error Handling

### 1. Graceful Degradation
- Fallback mechanisms
- Partial functionality maintenance
- User notification system

### 2. Recovery Strategies
- Automatic retry logic
- State preservation
- Context restoration

### 3. Logging and Monitoring
- Comprehensive error tracking
- Performance metrics
- User activity logging

---

This architecture provides a solid foundation for a scalable, maintainable, and user-friendly AI assistant system while maintaining security and extensibility.
