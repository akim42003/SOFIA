# Ollama Brain Implementation

The Ollama Brain provides local AI capabilities through the Ollama framework, enabling SOFIA to run entirely offline while maintaining full functionality with tool execution and conversation management.

## Overview

The Ollama Brain (`sofia/core/brain.py`) implements a local AI interface using the Ollama library. It provides the same capabilities as the OpenAI Brain but runs models locally, offering privacy, offline operation, and cost efficiency.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ollama Brain System                          │
├─────────────────────────────────────────────────────────────────┤
│  Local Model Interface                                          │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Ollama Client  │  │  Model          │                     │
│  │  (Local)        │  │  Management     │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Message Processing                                             │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Native Format  │  │  Tool Call      │                     │
│  │  (No Conversion)│  │  Processing     │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Tool Execution                                                 │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Function       │  │  Response       │                     │
│  │  Registry       │  │  Integration    │                     │
│  └─────────────────┘  └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Core Implementation

### Class Definition

```python
class ChatBrain:
    def __init__(self, chat_func):
        \"\"\"
        Initialize Ollama Brain with chat function

        Args:
            chat_func: Ollama chat function (typically ollama.chat)
        \"\"\"
        self.chat = chat_func
        self.available_functions = {
            \"save_file\": save_file,
            \"read_file\": read_file,
            \"execute_command\": execute_command,
            \"gmail_search_emails\": gmail_search_emails,
            \"gmail_fetch_emails\": fetch_gmail,
            \"gmail_send_emails\": send_gmail,
            \"reset_google_cred\": reset_google_cred,
            \"take_screenshot\": take_screenshot,
            \"move_mouse\": move_mouse,
            \"click_mouse\": click_mouse,
            \"drag_mouse\": drag_mouse,
            \"type_text\": type_text,
            \"press_key\": press_key,
            \"hotkey\": hotkey,
        }
```

### Model Configuration

The Ollama Brain uses models configured through Ollama's model system:

```bash
# Create custom SOFIA model
ollama create sofia2 -f ~/SOFIA/config/Modelfile.enhanced

# Available model commands
ollama list                    # List installed models
ollama pull mistral-small3.1:24b     # Download new model
ollama rm sofia2              # Remove model
```

### Enhanced Modelfile

The enhanced Modelfile (`config/Modelfile.enhanced`) defines SOFIA's behavior:

```dockerfile
FROM mistral-small3.1:24b

SYSTEM \"\"\"
You are SOFIA (Sort of Functional Interactive Agent), a personal AI productivity and life management assistant for {USER_NAME}.

## Core Capabilities

You have access to powerful tools that allow you to:
1. **Desktop Automation**: Take screenshots, control mouse/keyboard, analyze UI elements
2. **Email Management**: Search, read, compose, reply to Gmail messages
3. **File Operations**: Read/write files (sandboxed to ~/SOFIA/)
4. **System Commands**: Execute terminal commands

## Tool Usage Guidelines

### Desktop Automation
- Always take a screenshot first to understand the current state
- After performing actions (click, type, etc.), take another screenshot to verify results
- Use OmniParser integration for accurate UI element detection
- Chain multiple actions for complex workflows

### Verification Loop Behavior
When completing tasks:
1. Execute the requested action
2. Verify results (screenshot for UI, read for files)
3. Continue with additional tools if needed
4. Only report completion after verification
5. If results aren't as expected, retry or adjust approach

## Agent Behavior
You operate in a continuous loop:
- Analyze the request
- Plan the approach
- Execute tools in parallel when possible
- Verify results
- Continue until task is truly complete
- Report verified success or encountered issues

Remember: You're not just a chatbot - you're an agent that takes action and verifies results.
\"\"\"

PARAMETER temperature 1
PARAMETER num_ctx 32768
```

## Message Processing

Unlike OpenAI Brain, Ollama Brain uses SOFIA's native message format without conversion:

### Native Format Support

```python
def continuous_chat(self, messages: List[Dict], tools: List[Dict]) -> Tuple[str, str]:
    \"\"\"
    Handle chat interaction using native Ollama format

    Args:
        messages: Conversation history in SOFIA format
        tools: Tool definitions in SOFIA format

    Returns:
        Tuple[str, str]: (response_text, user_input)
    \"\"\"
    # Get user input
    user_input = input(\"User: \")
    messages.append({\"role\": \"user\", \"content\": user_input})

    # Call Ollama directly with native format
    response: ChatResponse = self.chat(
        \"sofia2\",
        messages=messages,
        tools=tools,
    )

    # Process response and tool calls
    if response.message.tool_calls:
        tool_executed = self.execute_tool_calls(response, messages)
        if tool_executed:
            # Get follow-up response after tool execution
            final_response: ChatResponse = self.chat(\"sofia2\", messages=messages, tools=tools)
            messages.append({\"role\": \"assistant\", \"content\": final_response.message.content})
            return final_response.message.content, user_input

    # Regular response without tools
    messages.append({\"role\": \"assistant\", \"content\": response.message.content})
    return response.message.content, user_input
```

### Streaming Support

```python
def streaming_chat(self, messages: List[Dict], tools: List[Dict]) -> Iterator[str]:
    \"\"\"
    Handle streaming chat with real-time response delivery

    Yields:
        str: Content chunks as they arrive
    \"\"\"
    full_response = \"\"
    tool_calls = []

    # Stream response from Ollama
    for chunk in self.chat(\"sofia2\", messages=messages, tools=tools, stream=True):
        # Yield content chunks
        content = chunk['message'].get('content', '')
        if content:
            full_response += content
            yield content

        # Collect tool calls
        if chunk['message'].get('tool_calls'):
            tool_calls.extend(chunk['message']['tool_calls'])

    # Execute accumulated tool calls
    if tool_calls:
        yield \"\\n\\n🛠️ Executing tools...\"

        # Create mock response for tool execution
        mock_response = type('MockResponse', (), {
            'message': type('Message', (), {'tool_calls': tool_calls})()
        })()

        self.execute_tool_calls(mock_response, messages)

        # Get final response
        for chunk in self.chat(\"sofia2\", messages=messages, tools=tools, stream=True):
            content = chunk['message'].get('content', '')
            if content:
                yield content
```

## Tool Execution

### Tool Call Processing

```python
def execute_tool_calls(self, response: ChatResponse, messages: List[Dict]) -> bool:
    \"\"\"
    Execute tool calls from Ollama response

    Args:
        response: Ollama chat response containing tool calls
        messages: Message history to append results to

    Returns:
        bool: True if any tools were executed successfully
    \"\"\"
    executed = False

    for tool in response.message.tool_calls:
        tool_name = tool.function.name
        args = tool.function.arguments

        # Parse arguments if they're a string
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception as e:
                print(\"Error parsing arguments:\", e)
                args = {}

        # Execute function
        func = self.available_functions.get(tool_name)
        if func:
            try:
                output = func(**args)
                print(f\"Calling function: {tool_name}\")
                print(\"Arguments:\", args)
                print(\"Function output:\", output)

                # Add tool result to messages
                messages.append({
                    \"role\": \"tool\",
                    \"content\": str(output),
                    \"name\": tool_name,
                })
                executed = True

                # Special processing for screenshots
                if tool_name == \"take_screenshot\":
                    self._process_screenshot(output, messages)

            except Exception as e:
                print(\"Error calling function:\", e)
                messages.append({
                    \"role\": \"tool\",
                    \"content\": f\"Error calling {tool_name}: {e}\",
                    \"name\": tool_name,
                })
        else:
            print(\"Function\", tool_name, \"not found\")
            messages.append({
                \"role\": \"tool\",
                \"content\": f\"Function {tool_name} not found\",
                \"name\": tool_name,
            })

    return executed
```

### Screenshot Processing

```python
def _process_screenshot(self, output: Dict, messages: List[Dict]):
    \"\"\"Process screenshot results with OmniParser integration\"\"\"
    path = output.get(\"path\")
    if path and os.path.exists(path):
        try:
            print(\"Processing screenshot with OmniParser\")
            from sofia.vision.omniparser import process_image
            image_content = process_image(path)

            # Add assistant message with image analysis
            messages.append({
                \"role\": \"assistant\",
                \"content\": image_content,
                \"images\": [path]
            })
        except Exception as e:
            print(f\"Error processing screenshot: {e}\")
            # Fallback without detailed analysis
            messages.append({
                \"role\": \"assistant\",
                \"content\": \"Screenshot taken successfully.\",
                \"images\": [path]
            })
```

## Configuration and Setup

### Model Installation

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull base model
ollama pull mistral-small3.1:24b

# Create SOFIA model
cd ~/SOFIA
ollama create sofia2 -f config/Modelfile.enhanced

# Verify installation
ollama list
ollama run sofia2 \"Hello, I'm testing SOFIA\"
```

### Model Customization

The Modelfile can be customized for different use cases:

```dockerfile
# High-performance configuration
FROM mistral-small3.1:24b
PARAMETER temperature 0.7
PARAMETER num_ctx 16384
PARAMETER top_p 0.9

# Creative configuration
FROM mistral-small3.1:24b
PARAMETER temperature 1.2
PARAMETER num_ctx 32768
PARAMETER top_k 40
```

### System Integration

```python
# In brain_factory.py
def create_ollama_brain() -> ChatBrain:
    \"\"\"Create Ollama brain with proper configuration\"\"\"
    from ollama import chat

    # Verify model exists
    try:
        # Test model availability
        chat(\"sofia2\", messages=[{\"role\": \"user\", \"content\": \"test\"}])
    except Exception as e:
        raise RuntimeError(
            f\"Ollama model 'sofia2' not available: {e}\\n\"
            \"Please run: ollama create sofia2 -f config/Modelfile.enhanced\"
        )

    return ChatBrain(chat)
```

## Performance Optimization

### Memory Management

```python
def _optimize_message_history(self, messages: List[Dict], max_messages: int = 20) -> List[Dict]:
    \"\"\"Optimize message history for local processing\"\"\"
    if len(messages) <= max_messages:
        return messages

    # Keep system messages and recent history
    system_messages = [m for m in messages if m['role'] == 'system']
    recent_messages = messages[-max_messages:]

    # Ensure we don't duplicate system messages
    filtered_recent = [m for m in recent_messages if m['role'] != 'system']

    return system_messages + filtered_recent

def _should_compress_images(self, messages: List[Dict]) -> bool:
    \"\"\"Determine if images should be compressed or removed\"\"\"
    image_count = sum(1 for m in messages if m.get('images'))
    return image_count > 5  # Keep only recent images
```

### Parallel Tool Execution

```python
def execute_parallel_tools(self, tool_calls: List, messages: List[Dict]) -> bool:
    \"\"\"Execute multiple tools in parallel for better performance\"\"\"
    import concurrent.futures

    def execute_single_tool(tool_call):
        tool_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
        func = self.available_functions.get(tool_name)

        if func:
            try:
                return tool_name, func(**args), None
            except Exception as e:
                return tool_name, None, str(e)
        else:
            return tool_name, None, f\"Function {tool_name} not found\"

    # Execute tools in parallel (for non-dependent operations)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(execute_single_tool, tool) for tool in tool_calls]

        executed = False
        for future in concurrent.futures.as_completed(futures):
            tool_name, output, error = future.result()

            if error:
                messages.append({
                    \"role\": \"tool\",
                    \"content\": f\"Error: {error}\",
                    \"name\": tool_name,
                })
            else:
                messages.append({
                    \"role\": \"tool\",
                    \"content\": str(output),
                    \"name\": tool_name,
                })
                executed = True

    return executed
```

## Integration with UI Components

### Desktop Application Integration

```python
# In analysis_thread.py
class AnalysisThread(QThread):
    def run(self):
        # Ollama-specific streaming implementation
        if not isinstance(self.brain, OpenAIChatBrain):
            response = \"\"
            for chunk in ollama.chat(
                model=\"sofia2\",
                messages=messages,
                tools=self.tools,
                stream=True
            ):
                # Handle tool calls during streaming
                if chunk['message'].get('tool_calls'):
                    self.brain.execute_tool_calls(chunk, messages)

                # Emit content chunks
                content = chunk['message'].get('content', '')
                if content:
                    response += content
                    self.streaming_chunk.emit(content)

            # Final response processing
            self.streaming_finished.emit(response)
```

### Web Application Integration

```python
# In gradio_app.py - Ollama-specific handling
else:
    # Use Ollama brain (existing logic)
    from ollama import chat
    stream = chat(\"sofia2\", messages=messages, tools=tools, stream=True)

    for chunk in stream:
        content = chunk[\"message\"].get(\"content\", \"\")
        init_content += content
        full_response += content

        # Real-time streaming to user
        yield gr.ChatMessage(
            role=\"assistant\",
            content=full_response,
            metadata={\"iteration\": iteration} if iteration > 1 else None
        )

        # Accumulate tool calls
        if chunk[\"message\"].get(\"tool_calls\"):
            has_tool_calls = True
            tool_calls.extend(chunk[\"message\"][\"tool_calls\"])
```

## Debugging and Troubleshooting

### Model Verification

```python
def verify_ollama_setup():
    \"\"\"Verify Ollama installation and model availability\"\"\"
    try:
        import ollama

        # Check if Ollama is running
        models = ollama.list()
        print(f\"Available models: {[m['name'] for m in models['models']]}\")

        # Check if SOFIA model exists
        sofia_models = [m for m in models['models'] if 'sofia' in m['name']]
        if not sofia_models:
            print(\"Warning: No SOFIA models found\")
            return False

        # Test model response
        response = ollama.chat(\"sofia2\", messages=[
            {\"role\": \"user\", \"content\": \"Test message\"}
        ])

        print(f\"Test response: {response['message']['content'][:100]}...\")
        return True

    except Exception as e:
        print(f\"Ollama setup error: {e}\")
        return False
```

### Performance Monitoring

```python
def monitor_performance(self, messages: List[Dict], start_time: float):
    \"\"\"Monitor and log performance metrics\"\"\"
    end_time = time.time()
    duration = end_time - start_time

    token_estimate = sum(len(str(m.get('content', ''))) for m in messages) // 4
    tokens_per_second = token_estimate / duration if duration > 0 else 0

    print(f\"Response time: {duration:.2f}s\")
    print(f\"Estimated tokens: {token_estimate}\")
    print(f\"Tokens/second: {tokens_per_second:.1f}\")

    # Log to file for analysis
    with open('~/SOFIA/logs/performance.log', 'a') as f:
        f.write(f\"{time.time()},{duration},{token_estimate},{tokens_per_second}\\n\")
```

## Advanced Features

### Custom Model Training Data

```python
def export_conversation_for_training(self, messages: List[Dict]) -> str:
    \"\"\"Export conversation in format suitable for model fine-tuning\"\"\"
    training_data = []

    for msg in messages:
        if msg['role'] in ['user', 'assistant']:
            training_data.append({
                \"role\": msg['role'],
                \"content\": msg['content']
            })

    return json.dumps(training_data, indent=2)

def create_custom_modelfile(self, user_name: str, custom_instructions: str) -> str:
    \"\"\"Generate custom Modelfile for specific use cases\"\"\"
    modelfile = f\"\"\"
FROM mistral-small3.1:24b

SYSTEM \"\"\"
You are SOFIA, a personal AI assistant for {user_name}.

{custom_instructions}

Remember to always use the available tools to help accomplish tasks effectively.
\"\"\"

PARAMETER temperature 0.8
PARAMETER num_ctx 16384
\"\"\"

    return modelfile
```

### Model Switching

```python
def switch_model(self, new_model: str):
    \"\"\"Switch to a different Ollama model dynamically\"\"\"
    try:
        # Test new model
        test_response = ollama.chat(new_model, messages=[
            {\"role\": \"user\", \"content\": \"Test\"}
        ])

        # Update model name in configuration
        self.current_model = new_model
        print(f\"Switched to model: {new_model}\")
        return True

    except Exception as e:
        print(f\"Failed to switch to model {new_model}: {e}\")
        return False

def list_available_models(self) -> List[str]:
    \"\"\"List all available Ollama models\"\"\"
    try:
        models = ollama.list()
        return [m['name'] for m in models['models']]
    except Exception as e:
        print(f\"Error listing models: {e}\")
        return []
```

## Testing

### Unit Tests

```python
def test_tool_execution():
    \"\"\"Test tool execution with mock functions\"\"\"
    brain = ChatBrain(mock_chat_function)

    # Mock response with tool call
    mock_response = type('Response', (), {
        'message': type('Message', (), {
            'tool_calls': [
                type('Tool', (), {
                    'function': type('Function', (), {
                        'name': 'test_function',
                        'arguments': '{\"param\": \"value\"}'
                    })()
                })()
            ]
        })()
    })()

    messages = []
    result = brain.execute_tool_calls(mock_response, messages)
    assert result == True
    assert len(messages) == 1

def test_streaming_response():
    \"\"\"Test streaming response processing\"\"\"
    brain = ChatBrain(mock_streaming_chat)
    messages = [{\"role\": \"user\", \"content\": \"Hello\"}]
    tools = []

    response_generator = brain.streaming_chat(messages, tools)
    full_response = \"\".join(response_generator)
    assert len(full_response) > 0
```

### Integration Tests

```python
def test_complete_conversation():
    \"\"\"Test complete conversation flow\"\"\"
    if not verify_ollama_setup():
        pytest.skip(\"Ollama not available\")

    brain = ChatBrain(ollama.chat)
    messages = [{\"role\": \"user\", \"content\": \"What's 2+2?\"}]
    tools = []

    response, user_input = brain.continuous_chat(messages, tools)
    assert \"4\" in response
    assert len(messages) == 3  # user, assistant, follow-up
```

The Ollama Brain provides a powerful, privacy-focused alternative to cloud-based AI while maintaining full compatibility with SOFIA's tool ecosystem and user interfaces.
