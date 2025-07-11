# Web Application

The SOFIA Web Application provides a browser-based interface built with Gradio, offering cross-platform accessibility, multimodal interaction, and real-time AI responses through an intuitive chat interface.

## Overview

The web application (`sofia/ui/web/gradio_app.py`) delivers a modern, responsive web interface that works across all platforms and devices, providing the same powerful SOFIA capabilities through any web browser.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Web Application                              │
├─────────────────────────────────────────────────────────────────┤
│  Gradio Framework                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  ChatInterface  │  │  Multimodal     │  │  Real-time      │ │
│  │  Component      │  │  Input Support  │  │  Streaming      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Message Processing                                             │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Response       │  │  Tool Execution │                     │
│  │  Handling       │  │  Feedback       │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Brain Integration                                              │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Dual Backend   │  │  Format         │                     │
│  │  Support        │  │  Conversion     │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Server Management                                              │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Network        │  │  Session        │                     │
│  │  Configuration  │  │  Management     │                     │
│  └─────────────────┘  └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Core Implementation

### Application Structure

```python
# Global variables for application state
brain = None
messages = []
tools = []
backend = \"ollama\"

def create_demo():
    \"\"\"Create and return the Gradio demo interface\"\"\"
    global brain, messages, tools, backend
    
    # Initialize brain and configuration
    brain, INITIAL_MESSAGES, TOOLS_SPEC = get_brain_and_config()
    
    # Clean initial messages - remove tool-related messages for fresh start
    cleaned_messages = []
    for msg in INITIAL_MESSAGES:
        if msg['role'] not in ['tool'] and not (msg['role'] == 'assistant' and 'tool_calls' in msg):
            cleaned_messages.append(msg)
    
    messages = cleaned_messages.copy()
    tools = TOOLS_SPEC.copy()
    
    # Determine backend for UI display
    config = load_sofia_config()
    backend = config.get('ai_backend', 'ollama')
    
    # Create Gradio ChatInterface
    demo = gr.ChatInterface(
        fn=respond,
        multimodal=True,
        title=f\"SOFIA Assistant ({backend.upper()} Backend)\",
        description=f\"Sort of Functional Interactive Agent - Running on {backend.upper()}\",
        examples=[
            {\"text\": \"Show me the current time\"},
            {\"text\": \"Take a screenshot and describe what you see\"},
            {\"text\": \"Check my recent emails\"},
        ],
        cache_examples=False,
    )
    
    return demo
```

### Response Handler

The core response function handles both text and multimodal input:

```python
def respond(msg, _):
    \"\"\"
    Main response handler for chat interface
    
    Args:
        msg: User message (dict with 'text' and 'files' keys or string)
        _: Chat history (handled internally by Gradio)
        
    Yields:
        gr.ChatMessage: Streaming response messages
    \"\"\"
    global tools
    
    # Parse input message
    text = msg.get(\"text\", \"\") if isinstance(msg, dict) else str(msg)
    files = msg.get(\"files\", []) if isinstance(msg, dict) else []
    
    # Build message entry
    entry = {\"role\": \"user\", \"content\": text}
    if files:
        entry[\"images\"] = files
    messages.append(entry)
    
    # Ensure tools are available
    if not tools:
        print(\"WARNING: No tools loaded!\")
        _, _, tools = get_brain_and_config()
    
    # Process with iteration limit for safety
    MAX_ITERATIONS = 10
    iteration = 0
    full_response = \"\"
    
    while iteration < MAX_ITERATIONS:
        iteration += 1
        init_content = \"\"
        has_tool_calls = False
        tool_calls = []
        
        # Process based on brain type
        if isinstance(brain, OpenAIChatBrain):
            yield from process_openai_request(messages, tools, iteration, full_response)
        else:
            yield from process_ollama_request(messages, tools, iteration, full_response)
        
        # Break if no tool calls
        if not has_tool_calls:
            break
    
    return
```

### OpenAI Processing

Specialized handling for OpenAI API integration:

```python
def process_openai_request(messages, tools, iteration, full_response):
    \"\"\"Process request using OpenAI brain\"\"\"
    from sofia.core.openai_brain import convert_messages_to_openai_format, convert_tools_to_openai_format
    
    # Convert formats
    openai_messages = convert_messages_to_openai_format(messages)
    openai_tools = convert_tools_to_openai_format(tools)
    
    try:
        # Make streaming API call
        stream = brain.client.chat.completions.create(
            model=brain.model,
            messages=openai_messages,
            tools=openai_tools if openai_tools else None,
            stream=True
        )
        
        init_content = \"\"
        tool_calls = []
        
        # Process streaming response
        for chunk in stream:
            delta = chunk.choices[0].delta
            
            if delta.content:
                init_content += delta.content
                full_response += delta.content
                
                yield gr.ChatMessage(
                    role=\"assistant\",
                    content=full_response,
                    metadata={\"iteration\": iteration} if iteration > 1 else None
                )
            
            # Accumulate tool calls
            if delta.tool_calls:
                has_tool_calls = True
                for tc in delta.tool_calls:
                    if tc.index >= len(tool_calls):
                        tool_calls.append({
                            \"id\": tc.id,
                            \"type\": \"function\",
                            \"function\": {
                                \"name\": tc.function.name if tc.function else None,
                                \"arguments\": tc.function.arguments if tc.function else \"\"
                            }
                        })
                    else:
                        if tc.function and tc.function.arguments:
                            tool_calls[tc.index][\"function\"][\"arguments\"] += tc.function.arguments
        
        # Execute tools if present
        if tool_calls:
            yield from execute_openai_tools(tool_calls, messages, init_content, full_response)
            
    except Exception as e:
        yield gr.ChatMessage(
            role=\"assistant\",
            content=f\"OpenAI Error: {str(e)}\"
        )
```

### Ollama Processing

Native Ollama integration with streaming:

```python
def process_ollama_request(messages, tools, iteration, full_response):
    \"\"\"Process request using Ollama brain\"\"\"
    from ollama import chat
    
    stream = chat(\"sofia2\", messages=messages, tools=tools, stream=True)
    
    init_content = \"\"
    tool_calls = []
    
    for chunk in stream:
        content = chunk[\"message\"].get(\"content\", \"\")
        init_content += content
        full_response += content
        
        yield gr.ChatMessage(
            role=\"assistant\",
            content=full_response,
            metadata={\"iteration\": iteration} if iteration > 1 else None
        )
        
        # Accumulate tool calls instead of executing immediately
        if chunk[\"message\"].get(\"tool_calls\"):
            has_tool_calls = True
            tool_calls.extend(chunk[\"message\"][\"tool_calls\"])
    
    # Execute accumulated tool calls
    if tool_calls:
        yield from execute_ollama_tools(tool_calls, messages, full_response)
```

### Tool Execution

#### OpenAI Tool Execution

```python
def execute_openai_tools(tool_calls, messages, init_content, full_response):
    \"\"\"Execute OpenAI tool calls with feedback\"\"\"
    
    yield gr.ChatMessage(
        role=\"assistant\",
        content=f\"{full_response}\\n\\n🛠️ Executing {len(tool_calls)} tool(s)...\"
    )
    
    # Add assistant message with tool calls
    messages.append({
        \"role\": \"assistant\",
        \"content\": init_content or \"\",
        \"tool_calls\": tool_calls
    })
    
    # Convert tool calls to objects and execute
    tool_objects = []
    for tc in tool_calls:
        tool_obj = type('ToolCall', (), {
            'id': tc['id'],
            'function': type('Function', (), {
                'name': tc['function']['name'],
                'arguments': tc['function']['arguments']
            })()
        })()
        tool_objects.append(tool_obj)
    
    brain.execute_tool_calls(tool_objects, messages)
    
    # Handle automatic screenshot for desktop actions
    desktop_tools = {\"move_mouse\", \"click_mouse\", \"drag_mouse\", \"type_text\", \"press_key\", \"hotkey\"}
    has_desktop_actions = any(tc['function']['name'] in desktop_tools for tc in tool_calls)
    
    if has_desktop_actions:
        handle_automatic_screenshot(messages)
    
    # Continue to next iteration
    full_response += \"\\n\\n\"
```

#### Ollama Tool Execution

```python
def execute_ollama_tools(tool_calls, messages, full_response):
    \"\"\"Execute Ollama tool calls with enhanced feedback\"\"\"
    
    yield gr.ChatMessage(
        role=\"assistant\",
        content=f\"{full_response}\\n\\n🛠️ Executing {len(tool_calls)} tool(s)...\"
    )
    
    # Create mock response for tool execution
    class MockResponse:
        class Message:
            def __init__(self, tool_calls):
                self.tool_calls = tool_calls
        def __init__(self, tool_calls):
            self.message = self.Message(tool_calls)
    
    combined_response = MockResponse(tool_calls)
    brain.execute_tool_calls(combined_response, messages)
    
    # Handle automatic screenshot for desktop actions
    desktop_tools = {\"move_mouse\", \"click_mouse\", \"drag_mouse\", \"type_text\", \"press_key\", \"hotkey\"}
    has_desktop_actions = any(tool.function.name in desktop_tools for tool in tool_calls)
    
    if has_desktop_actions:
        try:
            # Take automatic screenshot
            screenshot_result = brain.available_functions[\"take_screenshot\"]()
            messages.append({
                \"role\": \"tool\",
                \"content\": str(screenshot_result),
                \"name\": \"take_screenshot\"
            })
            
            # Process screenshot
            path = screenshot_result.get(\"path\")
            if path and os.path.exists(path):
                # For Ollama, skip OmniParser to avoid failures
                messages.append({
                    \"role\": \"assistant\",
                    \"content\": \"Desktop action completed - screenshot taken for verification.\",
                    \"images\": [path]
                })
                
        except Exception as screenshot_error:
            print(f\"Error taking screenshot: {screenshot_error}\")
    
    # Continue to next iteration
    full_response += \"\\n\\n\"
```

### Multimodal Support

Advanced handling for images and files:

```python
def handle_multimodal_input(msg):
    \"\"\"Process multimodal input (text + images/files)\"\"\"
    
    if isinstance(msg, dict):
        text = msg.get(\"text\", \"\")
        files = msg.get(\"files\", [])
    else:
        text = str(msg)
        files = []
    
    # Process uploaded files
    processed_files = []
    for file_path in files:
        if is_image_file(file_path):
            processed_files.append(file_path)
        else:
            # Handle other file types (future extension)
            print(f\"Unsupported file type: {file_path}\")
    
    return text, processed_files

def is_image_file(file_path: str) -> bool:
    \"\"\"Check if file is a supported image format\"\"\"
    if not os.path.exists(file_path):
        return False
    
    supported_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
    return Path(file_path).suffix.lower() in supported_extensions

def process_image_upload(image_path: str) -> Dict:
    \"\"\"Process uploaded image for analysis\"\"\"
    try:
        # Validate image
        if not is_image_file(image_path):
            return {\"error\": \"Invalid image format\"}
        
        # Get image info
        from PIL import Image
        with Image.open(image_path) as img:
            width, height = img.size
            format_name = img.format
        
        return {
            \"path\": image_path,
            \"width\": width,
            \"height\": height,
            \"format\": format_name,
            \"size\": os.path.getsize(image_path)
        }
        
    except Exception as e:
        return {\"error\": f\"Error processing image: {e}\"}
```

### Server Configuration

Production-ready server setup:

```python
def main():
    \"\"\"Main function to launch the Gradio app\"\"\"
    demo = create_demo()
    
    # Server configuration
    server_config = {
        \"server_name\": \"0.0.0.0\",  # Accept connections from any IP
        \"server_port\": 7860,        # Default Gradio port
        \"share\": False,             # Set to True for public sharing
        \"quiet\": False,             # Set to True for minimal logging
        \"ssl_verify\": False,        # Disable SSL verification if needed
        \"show_error\": True,         # Show detailed errors
    }
    
    # Load custom configuration if available
    config_path = Path(\"config/web_config.yaml\")
    if config_path.exists():
        import yaml
        with open(config_path, 'r') as f:
            custom_config = yaml.safe_load(f)
            server_config.update(custom_config)
    
    print(f\"Starting SOFIA Web Interface...\")
    print(f\"Backend: {backend.upper()}\")
    print(f\"Server: http://localhost:{server_config['server_port']}\")
    
    demo.launch(**server_config)

if __name__ == \"__main__\":
    main()
```

### Advanced Features

#### Custom CSS Styling

```python
def get_custom_css() -> str:
    \"\"\"Return custom CSS for enhanced UI styling\"\"\"
    return \"\"\"
    /* Custom SOFIA styling */
    .gradio-container {
        max-width: 1200px !important;
        margin: 0 auto;
    }
    
    .chat-interface {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 10px;
    }
    
    .message-bubble {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    .tool-execution {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        font-family: monospace;
    }
    
    .streaming-indicator {
        animation: pulse 1.5s ease-in-out infinite alternate;
    }
    
    @keyframes pulse {
        from { opacity: 0.6; }
        to { opacity: 1; }
    }
    \"\"\"

def apply_custom_theme():
    \"\"\"Apply custom theme to Gradio interface\"\"\"
    theme = gr.themes.Soft(
        primary_hue=\"blue\",
        secondary_hue=\"gray\",
        neutral_hue=\"slate\",
        font=gr.themes.GoogleFont(\"Inter\"),
        font_mono=gr.themes.GoogleFont(\"JetBrains Mono\"),
    ).set(
        body_background_fill=\"linear-gradient(135deg, #667eea 0%, #764ba2 100%)\",
        button_primary_background_fill=\"#4f46e5\",
        button_primary_background_fill_hover=\"#3730a3\",
    )
    
    return theme
```

#### Session Management

```python
class SessionManager:
    \"\"\"Manage user sessions and conversation history\"\"\"
    
    def __init__(self):
        self.sessions = {}
        self.max_sessions = 100
        self.session_timeout = 3600  # 1 hour
    
    def create_session(self, session_id: str = None) -> str:
        \"\"\"Create a new session\"\"\"
        if not session_id:
            session_id = self.generate_session_id()
        
        self.sessions[session_id] = {
            \"messages\": [],
            \"created\": time.time(),
            \"last_activity\": time.time(),
            \"tools\": [],
            \"brain\": None
        }
        
        self.cleanup_old_sessions()
        return session_id
    
    def get_session(self, session_id: str) -> Dict:
        \"\"\"Get session data\"\"\"
        if session_id in self.sessions:
            self.sessions[session_id][\"last_activity\"] = time.time()
            return self.sessions[session_id]
        return None
    
    def update_session(self, session_id: str, data: Dict):
        \"\"\"Update session data\"\"\"
        if session_id in self.sessions:
            self.sessions[session_id].update(data)
            self.sessions[session_id][\"last_activity\"] = time.time()
    
    def cleanup_old_sessions(self):
        \"\"\"Remove expired sessions\"\"\"
        current_time = time.time()
        expired_sessions = [
            sid for sid, data in self.sessions.items()
            if current_time - data[\"last_activity\"] > self.session_timeout
        ]
        
        for sid in expired_sessions:
            del self.sessions[sid]
        
        # Limit total sessions
        if len(self.sessions) > self.max_sessions:
            # Remove oldest sessions
            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1][\"last_activity\"]
            )
            
            sessions_to_remove = len(self.sessions) - self.max_sessions
            for i in range(sessions_to_remove):
                del self.sessions[sorted_sessions[i][0]]
    
    def generate_session_id(self) -> str:
        \"\"\"Generate unique session ID\"\"\"
        import uuid
        return str(uuid.uuid4())

# Global session manager
session_manager = SessionManager()
```

#### Performance Monitoring

```python
def monitor_performance():
    \"\"\"Monitor web app performance metrics\"\"\"
    
    metrics = {
        \"active_sessions\": len(session_manager.sessions),
        \"total_requests\": getattr(monitor_performance, 'request_count', 0),
        \"average_response_time\": getattr(monitor_performance, 'avg_response_time', 0),
        \"memory_usage\": get_memory_usage(),
        \"cpu_usage\": get_cpu_usage(),
    }
    
    return metrics

def get_memory_usage() -> float:
    \"\"\"Get current memory usage in MB\"\"\"
    import psutil
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

def get_cpu_usage() -> float:
    \"\"\"Get current CPU usage percentage\"\"\"
    import psutil
    return psutil.cpu_percent(interval=1)

def log_request_metrics(start_time: float, endpoint: str):
    \"\"\"Log request performance metrics\"\"\"
    end_time = time.time()
    response_time = end_time - start_time
    
    # Update counters
    if not hasattr(log_request_metrics, 'request_count'):
        log_request_metrics.request_count = 0
        log_request_metrics.total_response_time = 0
    
    log_request_metrics.request_count += 1
    log_request_metrics.total_response_time += response_time
    
    # Calculate average
    avg_response_time = log_request_metrics.total_response_time / log_request_metrics.request_count
    
    # Log metrics
    print(f\"Request: {endpoint} | Time: {response_time:.2f}s | Avg: {avg_response_time:.2f}s\")
```

### Deployment Configurations

#### Docker Support

```python
def create_docker_config():
    \"\"\"Generate Docker configuration for web app\"\"\"
    
    dockerfile = \"\"\"
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create SOFIA directory
RUN mkdir -p /app/SOFIA

# Expose port
EXPOSE 7860

# Set environment variables
ENV PYTHONPATH=/app
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# Run setup and start application
CMD [\"python\", \"setup.py\", \"--non-interactive\"] && [\"python\", \"-m\", \"sofia.ui.web.gradio_app\"]
\"\"\"
    
    docker_compose = \"\"\"
version: '3.8'

services:
  sofia-web:
    build: .
    ports:
      - \"7860:7860\"
    volumes:
      - ./SOFIA:/app/SOFIA
      - ./.env:/app/.env
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - \"80:80\"
      - \"443:443\"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - sofia-web
    restart: unless-stopped
\"\"\"
    
    return dockerfile, docker_compose
```

#### Production Configuration

```python
def get_production_config():
    \"\"\"Get production-ready configuration\"\"\"
    
    return {
        \"server_name\": \"0.0.0.0\",
        \"server_port\": 7860,
        \"share\": False,
        \"quiet\": True,
        \"show_error\": False,
        \"enable_queue\": True,
        \"max_threads\": 40,
        \"auth\": (\"admin\", \"secure_password\"),  # Enable authentication
        \"ssl_keyfile\": \"/path/to/keyfile.pem\",
        \"ssl_certfile\": \"/path/to/certfile.pem\",
        \"allowed_paths\": [\"/app/SOFIA\"],
        \"blocked_paths\": [\"/etc\", \"/var\", \"/root\"],
    }
```

## Testing

### Unit Tests

```python
def test_message_processing():
    \"\"\"Test message processing with different input types\"\"\"
    
    # Test text-only message
    text_msg = \"Hello SOFIA\"
    text, files = handle_multimodal_input(text_msg)
    assert text == \"Hello SOFIA\"
    assert files == []
    
    # Test multimodal message
    multimodal_msg = {
        \"text\": \"Analyze this image\",
        \"files\": [\"/path/to/image.png\"]
    }
    text, files = handle_multimodal_input(multimodal_msg)
    assert text == \"Analyze this image\"
    assert len(files) == 1

def test_session_management():
    \"\"\"Test session creation and management\"\"\"
    sm = SessionManager()
    
    # Create session
    session_id = sm.create_session()
    assert session_id in sm.sessions
    
    # Get session
    session = sm.get_session(session_id)
    assert session is not None
    assert \"messages\" in session
```

### Integration Tests

```python
def test_complete_web_flow():
    \"\"\"Test complete web application flow\"\"\"
    
    # Initialize demo
    demo = create_demo()
    assert demo is not None
    
    # Test response function
    test_message = \"Hello SOFIA\"
    responses = list(respond(test_message, []))
    
    assert len(responses) > 0
    assert isinstance(responses[0], gr.ChatMessage)
```

The Web Application provides a modern, accessible interface for SOFIA with full feature parity to the desktop application while offering the convenience of browser-based access and cross-platform compatibility.