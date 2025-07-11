# OpenAI Brain Implementation

The OpenAI Brain provides cloud-based AI capabilities through the OpenAI API, enabling SOFIA to leverage powerful models like GPT-4o while maintaining compatibility with the existing tool system and message formats.

## Overview

The OpenAI Brain (`sofia/core/openai_brain.py`) implements a complete interface to OpenAI's Chat Completions API, including streaming responses, tool calling, and vision capabilities. It handles the complex message format conversions required to bridge SOFIA's internal format with OpenAI's API requirements.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenAI Brain System                         │
├─────────────────────────────────────────────────────────────────┤
│  API Client Layer                                              │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  OpenAI Client  │  │  API Key        │                     │
│  │  (Official SDK) │  │  Management     │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Message Processing                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Format         │  │  Tool Call      │  │  Image          │ │
│  │  Conversion     │  │  Handling       │  │  Encoding       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Streaming & Execution                                          │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Response       │  │  Tool           │                     │
│  │  Streaming      │  │  Execution      │                     │
│  └─────────────────┘  └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Core Implementation

### Class Definition

```python
class OpenAIChatBrain:
    def __init__(self, api_key: Optional[str] = None, model: str = \"gpt-4o\"):
        \"\"\"
        Initialize OpenAI Brain with API configuration
        
        Args:
            api_key: OpenAI API key (loaded from multiple sources if not provided)
            model: Model name to use (default: gpt-4o)
            
        Raises:
            ValueError: If no valid API key found
        \"\"\"
        # Multi-source API key loading
        self.api_key = self._load_api_key(api_key)
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.available_functions = self._initialize_functions()
```

### API Key Management

The OpenAI Brain implements a robust API key loading system with multiple fallback sources:

```python
def _load_api_key(self, provided_key: Optional[str]) -> str:
    \"\"\"Load API key from multiple sources with priority order\"\"\"
    
    # 1. Direct parameter (highest priority)
    if provided_key:
        return provided_key
    
    # 2. .env file
    env_vars = load_env_file()
    env_key = env_vars.get(\"OPENAI_API_KEY\")
    if env_key:
        return env_key
    
    # 3. Environment variable
    os_key = os.getenv(\"OPENAI_API_KEY\")
    if os_key:
        return os_key
    
    # 4. Fail with helpful error message
    raise ValueError(
        \"OpenAI API key not provided. Set it in:\\n\"
        \"1. .env file: OPENAI_API_KEY=your-key\\n\"
        \"2. Pass api_key parameter\\n\"
        \"3. Environment variable: export OPENAI_API_KEY='your-key'\"
    )
```

## Message Format Conversion

One of the most complex aspects of the OpenAI Brain is converting between SOFIA's internal message format and OpenAI's strict API requirements.

### Conversion Function

```python
def convert_messages_to_openai_format(messages: List[Dict]) -> List[Dict]:
    \"\"\"
    Convert SOFIA messages to OpenAI API format
    
    Handles:
    - Tool message orphan detection
    - Image URL formatting for vision API
    - Role conversion for assistant messages with images
    - Tool call ID tracking
    \"\"\"
    openai_messages = []
    tool_call_tracker = {}  # Track tool_call_ids for proper sequencing
    
    for i, msg in enumerate(messages):
        if msg['role'] == 'tool':
            # Handle tool response messages
            openai_msg = process_tool_message(msg, tool_call_tracker, messages, i)
        elif msg['role'] == 'assistant' and 'tool_calls' in msg:
            # Handle assistant messages with tool calls
            openai_msg = process_assistant_tool_message(msg, tool_call_tracker)
        else:
            # Handle regular messages (user, assistant, system)
            openai_msg = process_regular_message(msg)
        
        if openai_msg:  # Some messages may be skipped
            openai_messages.append(openai_msg)
    
    return openai_messages
```

### Tool Message Processing

```python
def process_tool_message(msg: Dict, tracker: Dict, messages: List, index: int) -> Optional[Dict]:
    \"\"\"Process tool response messages with orphan detection\"\"\"
    tool_name = msg.get('name', 'unknown')
    
    # Check if this tool has a corresponding tool_call
    if tool_name in tracker:
        # Normal tool response
        return {
            \"role\": \"tool\",
            \"content\": msg['content'],
            \"tool_call_id\": tracker.pop(tool_name)
        }
    else:
        # Orphaned tool message (like automatic screenshots)
        if tool_name == 'take_screenshot':
            # Check if next message is assistant with images
            next_msg_has_images = (
                index + 1 < len(messages) and 
                messages[index + 1]['role'] == 'assistant' and 
                'images' in messages[index + 1]
            )
            
            if next_msg_has_images:
                # Skip - will be handled by next message
                return None
            else:
                # Convert to assistant message
                return {
                    \"role\": \"assistant\",
                    \"content\": f\"I took a screenshot: {msg['content']}\"
                }
        else:
            # Convert other orphaned tools to assistant messages
            return {
                \"role\": \"assistant\", 
                \"content\": f\"Tool {tool_name} result: {msg['content']}\"
            }
```

### Image Processing

OpenAI's Vision API requires specific formatting for images:

```python
def process_image_message(msg: Dict) -> Dict:
    \"\"\"Process messages containing images for Vision API\"\"\"
    content_parts = []
    
    # Add text content
    if msg.get('content'):
        content_parts.append({
            \"type\": \"text\",
            \"text\": msg['content']
        })
    
    # Process images
    for image_path in msg.get('images', []):
        if os.path.exists(image_path):
            base64_image = encode_image_to_base64(image_path)
            if base64_image:
                # Determine image format
                image_format = get_image_format(image_path)
                
                content_parts.append({
                    \"type\": \"image_url\",
                    \"image_url\": {
                        \"url\": f\"data:image/{image_format};base64,{base64_image}\",
                        \"detail\": \"high\"  # High detail for better analysis
                    }
                })
    
    # OpenAI only allows images in user messages
    role = \"user\" if msg['role'] == 'assistant' else msg['role']
    if msg['role'] == 'assistant':
        # Add prefix to indicate this was originally an assistant message
        content_parts[0]['text'] = f\"[System analysis: {content_parts[0]['text']}]\"
    
    return {
        \"role\": role,
        \"content\": content_parts
    }
```

### Base64 Image Encoding

```python
def encode_image_to_base64(image_path: str) -> Optional[str]:
    \"\"\"
    Encode image to base64 for OpenAI Vision API
    
    Args:
        image_path: Path to image file
        
    Returns:
        Base64 encoded string or None if error
    \"\"\"
    try:
        with open(image_path, \"rb\") as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded
    except Exception as e:
        print(f\"Error encoding image {image_path}: {e}\")
        return None

def get_image_format(image_path: str) -> str:
    \"\"\"Determine image format from file extension\"\"\"
    ext = image_path.lower()
    if ext.endswith(('.jpg', '.jpeg')):
        return \"jpeg\"
    elif ext.endswith('.webp'):
        return \"webp\"
    else:
        return \"png\"  # Default
```

## Tool Integration

### Tool Format Conversion

```python
def convert_tools_to_openai_format(tools: List[Dict]) -> List[Dict]:
    \"\"\"Convert SOFIA tools to OpenAI function format\"\"\"
    openai_tools = []
    
    for tool in tools:
        if tool.get('type') == 'function':
            func = tool.get('function', {})
            openai_tool = {
                \"type\": \"function\",
                \"function\": {
                    \"name\": func.get('name'),
                    \"description\": func.get('description'),
                    \"parameters\": func.get('parameters', {})
                }
            }
            openai_tools.append(openai_tool)
    
    return openai_tools
```

### Tool Execution

```python
def execute_tool_calls(self, tool_calls, messages) -> bool:
    \"\"\"
    Execute OpenAI tool calls and add results to message history
    
    Args:
        tool_calls: List of tool call objects from OpenAI response
        messages: Message history to append results to
        
    Returns:
        bool: True if any tools were executed successfully
    \"\"\"
    executed = False
    
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        tool_call_id = tool_call.id
        
        # Parse arguments
        try:
            args = json.loads(tool_call.function.arguments)
        except Exception as e:
            print(f\"Error parsing arguments: {e}\")
            args = {}
        
        # Execute function
        func = self.available_functions.get(tool_name)
        if func:
            try:
                output = func(**args)
                print(f\"Calling function: {tool_name}\")
                print(\"Arguments:\", args)
                print(\"Function output:\", output)
                
                # Add tool response with proper tool_call_id
                messages.append({
                    \"role\": \"tool\",
                    \"content\": str(output),
                    \"tool_call_id\": tool_call_id,
                    \"name\": tool_name
                })
                executed = True
                
                # Handle special processing for screenshots
                if tool_name == \"take_screenshot\":
                    self._process_screenshot_result(output, messages)
                    
            except Exception as e:
                print(f\"Error calling function: {e}\")
                messages.append({
                    \"role\": \"tool\",
                    \"content\": f\"Error calling {tool_name}: {e}\",
                    \"tool_call_id\": tool_call_id,
                    \"name\": tool_name
                })
        else:
            print(f\"Function {tool_name} not found\")
            messages.append({
                \"role\": \"tool\",
                \"content\": f\"Function {tool_name} not found\",
                \"tool_call_id\": tool_call_id,
                \"name\": tool_name
            })
    
    return executed
```

### Screenshot Processing

```python
def _process_screenshot_result(self, output: Dict, messages: List[Dict]):
    \"\"\"Process screenshot results and add image analysis\"\"\"
    path = output.get(\"path\")
    if path and os.path.exists(path):
        try:
            print(\"Processing screenshot with OmniParser\")
            from sofia.vision.omniparser import process_image
            image_content = process_image(path)
            
            # Add assistant message with image and analysis
            messages.append({
                \"role\": \"assistant\",
                \"content\": image_content,
                \"images\": [path]
            })
        except Exception as e:
            print(f\"Error processing screenshot: {e}\")
            # Add simple message without detailed analysis
            messages.append({
                \"role\": \"assistant\",
                \"content\": \"Screenshot taken successfully.\",
                \"images\": [path]
            })
```

## Streaming Implementation

### Basic Streaming Chat

```python
def continuous_chat(self, messages: List[Dict], tools: List[Dict], stream: bool = False):
    \"\"\"
    Handle a single chat interaction with streaming support
    
    Args:
        messages: Conversation history
        tools: Available tool definitions
        stream: Enable streaming responses
        
    Returns:
        Tuple[str, str]: (response_text, user_input)
    \"\"\"
    user_input = input(\"User: \")
    messages.append({\"role\": \"user\", \"content\": user_input})
    
    # Convert to OpenAI format
    openai_messages = convert_messages_to_openai_format(messages)
    openai_tools = convert_tools_to_openai_format(tools)
    
    # Make API call
    response = self.client.chat.completions.create(
        model=self.model,
        messages=openai_messages,
        tools=openai_tools if openai_tools else None,
        stream=stream
    )
    
    if stream:
        return self._handle_streaming_response(response, messages, tools)
    else:
        return self._handle_standard_response(response, messages, tools)
```

### Streaming Response Processing

```python
def _handle_streaming_response(self, response, messages: List[Dict], tools: List[Dict]):
    \"\"\"Process streaming response with tool call accumulation\"\"\"
    full_content = \"\"
    tool_calls = []
    
    for chunk in response:
        delta = chunk.choices[0].delta
        
        # Accumulate content
        if delta.content:
            full_content += delta.content
            print(delta.content, end='', flush=True)
        
        # Accumulate tool calls
        if delta.tool_calls:
            for tc in delta.tool_calls:
                # Extend tool_calls list if needed
                while tc.index >= len(tool_calls):
                    tool_calls.append({
                        \"id\": None,
                        \"type\": \"function\",
                        \"function\": {\"name\": None, \"arguments\": \"\"}
                    })
                
                # Update tool call data
                if tc.id:
                    tool_calls[tc.index][\"id\"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_calls[tc.index][\"function\"][\"name\"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls[tc.index][\"function\"][\"arguments\"] += tc.function.arguments
    
    print()  # New line after streaming
    
    # Process tool calls if any
    if tool_calls:
        return self._execute_tools_and_continue(full_content, tool_calls, messages, tools)
    else:
        messages.append({\"role\": \"assistant\", \"content\": full_content})
        return full_content, None
```

### Tool Execution and Continuation

```python
def _execute_tools_and_continue(self, content: str, tool_calls: List[Dict], 
                               messages: List[Dict], tools: List[Dict]):
    \"\"\"Execute tools and get follow-up response\"\"\"
    
    # Add assistant message with tool calls
    messages.append({
        \"role\": \"assistant\",
        \"content\": content or \"\",
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
    
    # Execute tools
    self.execute_tool_calls(tool_objects, messages)
    
    # Get final response after tool execution
    final_response_text, _ = self.continuous_chat_no_input(messages, tools, stream=True)
    return final_response_text, None
```

## Error Handling

### API Error Management

```python
def _handle_api_error(self, error: Exception) -> str:
    \"\"\"Handle OpenAI API errors with helpful messages\"\"\"
    error_str = str(error)
    
    if \"Invalid parameter: messages with role 'tool'\" in error_str:
        return \"Error: Tool message format issue. Please check tool call sequence.\"
    elif \"Image URLs are only allowed for messages with role 'user'\" in error_str:
        return \"Error: Image processing issue. Retrying with corrected format.\"
    elif \"rate_limit_exceeded\" in error_str:
        return \"Error: API rate limit exceeded. Please wait before retrying.\"
    elif \"insufficient_quota\" in error_str:
        return \"Error: API quota exceeded. Please check your OpenAI account.\"
    else:
        return f\"OpenAI API Error: {error_str}\"
```

### Retry Logic

```python
def _make_api_call_with_retry(self, **kwargs) -> Any:
    \"\"\"Make API call with exponential backoff retry\"\"\"
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            return self.client.chat.completions.create(**kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            # Exponential backoff
            delay = base_delay * (2 ** attempt)
            print(f\"API call failed (attempt {attempt + 1}), retrying in {delay}s...\")
            time.sleep(delay)
```

## Usage Examples

### Basic Chat Implementation

```python
from sofia.core.openai_brain import OpenAIChatBrain, load_config

# Initialize brain
brain = OpenAIChatBrain(model=\"gpt-4o\")

# Load configuration
messages, tools = load_config()

# Start conversation
brain.initialize_chat(messages, tools)
```

### Web Interface Integration

```python
# In Gradio app
if isinstance(brain, OpenAIChatBrain):
    # Convert formats
    openai_messages = convert_messages_to_openai_format(messages)
    openai_tools = convert_tools_to_openai_format(tools)
    
    # Stream response
    stream = brain.client.chat.completions.create(
        model=brain.model,
        messages=openai_messages,
        tools=openai_tools,
        stream=True
    )
    
    for chunk in stream:
        # Process streaming chunks
        pass
```

### Desktop Application Integration

```python
# In PyQt application
class AnalysisThread(QThread):
    def run(self):
        if isinstance(self.brain, OpenAIChatBrain):
            # Handle OpenAI streaming
            response = self.brain.client.chat.completions.create(
                model=self.brain.model,
                messages=openai_messages,
                tools=openai_tools,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    self.streaming_chunk.emit(chunk.choices[0].delta.content)
```

## Performance Considerations

### Memory Management

```python
def _cleanup_old_messages(self, messages: List[Dict], max_length: int = 50):
    \"\"\"Keep conversation history manageable\"\"\"
    if len(messages) > max_length:
        # Keep system message and recent messages
        system_msgs = [m for m in messages[:5] if m['role'] == 'system']
        recent_msgs = messages[-max_length:]
        return system_msgs + recent_msgs
    return messages
```

### Token Optimization

```python
def _estimate_tokens(self, messages: List[Dict]) -> int:
    \"\"\"Rough token estimation for cost management\"\"\"
    total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
    return total_chars // 4  # Rough approximation

def _should_compress_history(self, messages: List[Dict]) -> bool:
    \"\"\"Determine if message history should be compressed\"\"\"
    estimated_tokens = self._estimate_tokens(messages)
    return estimated_tokens > 8000  # Stay well under context limits
```

## Testing

### Unit Tests

```python
def test_message_conversion():
    \"\"\"Test message format conversion\"\"\"
    sofia_messages = [
        {\"role\": \"user\", \"content\": \"Hello\"},
        {\"role\": \"assistant\", \"content\": \"Hi there!\"}
    ]
    
    openai_messages = convert_messages_to_openai_format(sofia_messages)
    assert len(openai_messages) == 2
    assert openai_messages[0]['role'] == 'user'

def test_tool_conversion():
    \"\"\"Test tool format conversion\"\"\"
    sofia_tools = [{
        \"type\": \"function\",
        \"function\": {
            \"name\": \"test_tool\",
            \"description\": \"Test function\"
        }
    }]
    
    openai_tools = convert_tools_to_openai_format(sofia_tools)
    assert len(openai_tools) == 1
    assert openai_tools[0]['function']['name'] == 'test_tool'
```

### Integration Tests

```python
def test_complete_chat_flow():
    \"\"\"Test complete chat flow with tool execution\"\"\"
    brain = OpenAIChatBrain(api_key=\"test_key\")
    messages = [{\"role\": \"user\", \"content\": \"Take a screenshot\"}]
    tools = [screenshot_tool_definition]
    
    # Mock API response
    with mock.patch.object(brain.client.chat.completions, 'create'):
        response = brain.continuous_chat(messages, tools)
        assert response is not None
```

The OpenAI Brain provides a robust, feature-complete interface to OpenAI's powerful AI models while maintaining seamless integration with SOFIA's tool system and user interfaces.