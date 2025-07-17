# SOFIA Architecture

SOFIA employs a modular, layered architecture designed for flexibility, security, and extensibility. The system supports multiple interfaces, AI backends, and tool integrations while maintaining strict security boundaries.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SOFIA System                            │
├─────────────────────────────────────────────────────────────────┤
│  User Interfaces                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  Desktop App    │  │   Web App       │  │  MCP Server     ││
│  │  (PyQt6)        │  │  (Gradio)       │  │  (FastMCP)      ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  Core Brain System                                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │          Brain Factory (Dynamic Backend Selection)          ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Ollama Brain   │  │  OpenAI Brain   │                     │
│  │  (Local Models) │  │  (Cloud Models) │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Tool & Integration Layer                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  Desktop Tools  │  │  System Tools   │  │  Gmail/Calendar ││
│  │  (UI Automation)│  │  (File/Command) │  │  (Google APIs)  ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Vision Tools   │  │  Audio Tools    │                     │
│  │  (OmniParser)   │  │  (Whisper)      │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Configuration & Security Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  Path Sandbox   │  │  Config Manager │  │  Auth Provider  ││
│  │  (~/SOFIA/)     │  │  (YAML/Env)     │  │  (OAuth2/Keys)  ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### User Interface Layer

#### Desktop Application (`sofia_desktop.py`)
- **Technology**: PyQt6 with transparent overlay design
- **Key Features**:
  - Frameless window with adjustable opacity
  - Real-time streaming responses
  - Drag-and-drop image support
  - System tray integration
  - Keyboard shortcuts (Ctrl+Shift+S)
- **Architecture**: Event-driven with threaded AI processing

#### Web Application (`sofia_web.py`)
- **Technology**: Gradio framework
- **Key Features**:
  - Browser-based multimodal interface
  - Audio file transcription
  - Real-time tool execution feedback
  - Conversation history management
  - Cross-platform accessibility
- **Port**: 7860 (configurable)

#### MCP Server (`sofia_gmail.py`)
- **Technology**: FastMCP with Model Context Protocol
- **Services**:
  - Gmail integration (search, send, reply, forward)
  - Google Calendar management
  - OAuth2 authentication flow
- **Port**: 3000 (standard MCP)

### Brain System Layer

#### Brain Factory Pattern
- **Purpose**: Dynamic AI backend selection and instantiation
- **Implementation**:
  ```python
  create_brain() → load_config() → select_backend() → instantiate_brain()
  ```
- **Benefits**:
  - Runtime backend switching
  - Configuration-driven selection
  - Consistent interface across backends

#### Ollama Brain (`sofia/core/brain.py`)
- **Models**: Custom sofia model, mistral-small3.1:24b, llama4
- **Features**:
  - Local inference with complete privacy
  - Streaming token generation
  - Tool call parsing and execution
  - Context window management
- **Requirements**: CUDA GPU (8GB+ VRAM recommended)

#### OpenAI Brain (`sofia/core/openai_brain.py`)
- **Models**: gpt-4o, gpt-4, gpt-3.5-turbo
- **Features**:
  - Cloud-based inference
  - Vision API for image analysis
  - Advanced function calling
  - Automatic retry with exponential backoff
- **Authentication**: API key via environment variable

### Tool System Architecture

#### Desktop Automation Tools
- **Screenshot Capture**: Full screen or region capture with PIL
- **Mouse Control**: Absolute/relative positioning, clicking, dragging
- **Keyboard Input**: Text typing, key presses, hotkey combinations
- **Implementation**: PyAutoGUI with error handling and verification

#### System Tools
- **File Operations**: Read/write with automatic path sandboxing
- **Command Execution**: Shell commands with timeout protection
- **Path Security**: All operations restricted to ~/SOFIA/ directory
- **Error Handling**: Graceful degradation with informative messages

#### Vision Processing (OmniParser)
- **Architecture**:
  ```
  Screenshot → YOLO Detection → Florence2/BLIP2 Captioning → Coordinate Mapping
  ```
- **Capabilities**:
  - UI element detection with bounding boxes
  - Text extraction from images
  - Natural language to pixel coordinate mapping
- **Performance**: GPU-accelerated inference

#### Google Service Integration
- **Gmail Tools**:
  - Search with advanced query syntax
  - Full message management (fetch, send, reply, forward)
  - Attachment handling
  - Label and thread support
- **Calendar Tools**:
  - Event creation with natural language parsing
  - Recurring event support
  - Availability checking
  - Timezone handling

### Security Architecture

#### Path Sandboxing
- **Implementation**: Automatic path normalization to ~/SOFIA/
- **Protection**: Directory traversal prevention
- **Validation**: Real-time path checking before operations
- **User Notification**: Clear error messages for violations

#### Authentication & Secrets
- **API Keys**: Environment variable storage
- **OAuth2**: Secure token management for Google services
- **Configuration**: Separation of secrets from code
- **Templates**: .env.template for easy setup

#### Tool Execution Safety
- **Parameter Validation**: Type checking and bounds verification
- **Timeout Protection**: Configurable execution limits
- **Error Recovery**: Automatic retry with exponential backoff
- **Audit Trail**: Comprehensive logging of all operations

## Data Flow Patterns

### Request Processing Pipeline
```
1. User Input → Interface Layer
2. Message Formation → Brain Selection
3. Context Addition → AI Processing
4. Tool Call Detection → Parameter Extraction
5. Tool Execution → Result Integration
6. Response Generation → User Display
```

### Tool Execution Flow
```
1. Function Call → Parameter Validation
2. Security Check → Path Sandboxing
3. Execution → Error Handling
4. Result Processing → Format Conversion
5. Response Integration → Context Update
```

### Concurrent Execution Model
- **Parallel Tool Calls**: Multiple operations in single request
- **Thread Pool**: Managed execution environment
- **Result Aggregation**: Ordered response assembly
- **Progress Tracking**: Real-time status updates

## Configuration Management

### Hierarchical Configuration
```
1. Environment Variables (highest priority)
2. User Configuration (~/SOFIA/config/user_config.yaml)
3. System Configuration (config/sofia_config.yaml)
4. Tool Definitions (config/tools.yaml)
5. Default Values (lowest priority)
```

### Dynamic Reconfiguration
- **Backend Switching**: `switch_backend.py` utility
- **Hot Reload**: Configuration changes without restart
- **Validation**: Schema checking on load
- **Migration**: Automatic config version updates

## Performance Optimization

### Memory Management
- **Screenshot Optimization**: Efficient PIL/NumPy conversions
- **Streaming Responses**: Token-by-token delivery
- **Context Pruning**: Automatic conversation trimming
- **Resource Pooling**: Reusable connections and objects

### Latency Reduction
- **Tool Prefetching**: Predictive resource loading
- **Caching**: Response and image caching
- **Batch Processing**: Grouped API calls
- **Async Operations**: Non-blocking I/O

### Scalability Considerations
- **Stateless Design**: Horizontal scaling ready
- **Queue Management**: Task distribution support
- **Load Balancing**: Multi-instance capability
- **Resource Limits**: Configurable constraints

## Extensibility Framework

### Adding New Tools
1. Define function in appropriate module
2. Add OpenAPI schema to tools.yaml
3. Register in brain's available_functions
4. Implement error handling and validation

### Custom AI Backends
1. Implement brain interface contract
2. Add factory method to brain_factory.py
3. Update configuration schema
4. Document model requirements

### Interface Extensions
1. Implement message processing protocol
2. Handle tool execution lifecycle
3. Integrate with brain factory
4. Add configuration support

## Error Handling Strategy

### Graceful Degradation
- **Fallback Mechanisms**: Alternative execution paths
- **Partial Success**: Complete available operations
- **User Communication**: Clear error messaging
- **State Preservation**: Recovery without data loss

### Logging Architecture
- **Structured Logging**: JSON format for analysis
- **Log Levels**: Configurable verbosity
- **Performance Metrics**: Execution time tracking
- **Error Tracking**: Stack traces and context

## Future Architecture Considerations

### Planned Enhancements
- **Plugin System**: Dynamic tool loading
- **Distributed Execution**: Multi-node support
- **Advanced Caching**: Intelligent result storage
- **WebSocket Support**: Real-time bidirectional communication

### Scalability Roadmap
- **Microservices**: Service-oriented architecture
- **Container Orchestration**: Kubernetes deployment
- **Message Queue**: Asynchronous task processing
- **API Gateway**: Rate limiting and authentication