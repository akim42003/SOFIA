# Ollama Brain Implementation

The Ollama Brain provides local AI capabilities through the Ollama framework, enabling SOFIA to run entirely offline while maintaining full functionality with tool execution and conversation management.

## Overview

The Ollama Brain (`sofia/core/brain.py`) implements a local AI interface using the Ollama library. It provides the same capabilities as the OpenAI Brain but runs models locally, offering privacy, offline operation, and cost efficiency. The brain features automatic memory management, screenshot optimization, and robust error handling for production use.

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
        Initialize Ollama Brain with chat function and memory management

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
            \"calendar_list_events\": calendar_list_events,
            \"calendar_create_event\": calendar_create_event,
            \"calendar_search_events\": calendar_search_events,
            \"calendar_delete_event\": calendar_delete_event,
            \"reset_google_cred\": reset_google_cred,
            \"take_screenshot\": take_screenshot,
            \"move_mouse\": move_mouse,
            \"click_mouse\": click_mouse,
            \"drag_mouse\": drag_mouse,
            \"type_text\": type_text,
            \"press_key\": press_key,
            \"hotkey\": hotkey,
        }

        # Memory management settings
        self.MAX_SCREENSHOT_MESSAGES = 5
        self.MAX_TOTAL_MESSAGES = 50
```

### Model Configuration

The Ollama Brain uses models configured through Ollama's model system:

```bash
# Create custom SOFIA model
ollama create sofia2 -f ~/SOFIA/config/Modelfile.enhanced
```

### Enhanced Modelfile

The enhanced Modelfile (`config/Modelfile.enhanced`) defines SOFIA's behavior:

## Memory Management and Optimization

The Ollama Brain includes robust memory management features to handle long-running conversations and resource-intensive operations:

### Automatic Message Cleanup

```python
def cleanup_old_messages(self, messages):
    \"\"\"Clean up old messages to prevent memory accumulation\"\"\"
    # First, clean up excess screenshot messages
    screenshot_count = 0
    cleaned_messages = []

    # Process messages in reverse order to keep the most recent screenshots
    for msg in reversed(messages):
        if msg.get('role') == 'assistant' and msg.get('images'):
            if screenshot_count < self.MAX_SCREENSHOT_MESSAGES:
                cleaned_messages.insert(0, msg)
                screenshot_count += 1
            # Skip older screenshot messages
        elif msg.get('role') == 'tool' and msg.get('name') == 'take_screenshot':
            if screenshot_count < self.MAX_SCREENSHOT_MESSAGES:
                cleaned_messages.insert(0, msg)
                # Don't increment counter for tool messages, only for image messages
            # Skip older screenshot tool messages
        else:
            cleaned_messages.insert(0, msg)

    # Then, limit total message count
    if len(cleaned_messages) > self.MAX_TOTAL_MESSAGES:
        # Keep the most recent messages
        cleaned_messages = cleaned_messages[-self.MAX_TOTAL_MESSAGES:]

    return cleaned_messages
```

### Screenshot Processing with Error Handling

The brain includes comprehensive screenshot processing with retry logic and resource management:

```python
# Handle screenshot processing with delays, retries, and helpful error messages
if tool_name == \"take_screenshot\":
    path = output.get(\"path\")
    if path and os.path.exists(path):
        # Add delay before processing to prevent resource overload
        time.sleep(1.0)

        # Retry logic for OmniParser processing
        max_retries = 2
        retry_delay = 2.0

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    print(f\"OmniParser retry attempt {attempt}/{max_retries}\")
                    time.sleep(retry_delay)
                else:
                    print(\"processing images with OmniParser\")

                # Force cleanup before processing
                import gc
                gc.collect()

                # Clear CUDA cache if available
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except:
                    pass

                # Process with OmniParser
                image_content = process_image(path)
                messages.append({
                    \"role\": \"assistant\",
                    \"content\": image_content,
                    \"images\": [path]
                })

                # Force cleanup after successful processing
                gc.collect()
                break  # Success - exit retry loop

            except Exception as omni_error:
                print(f\"OmniParser processing failed (attempt {attempt + 1}): {omni_error}\")

                if attempt == max_retries:
                    # Final attempt failed - provide helpful error message
                    error_message = (
                        \"Screenshot captured, but visual analysis failed due to resource overload. \"
                        \"The system's vision processing models (GPU/CPU) are temporarily overwhelmed. \"
                        \"Please wait 5-10 seconds before taking another screenshot to allow the system to recover. \"
                        \"The screenshot image is still available for viewing.\"
                    )
                    messages.append({
                        \"role\": \"assistant\",
                        \"content\": error_message,
                        \"images\": [path]
                    })

                # Force cleanup on error
                import gc
                gc.collect()
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except:
                    pass
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

The Ollama Brain provides a powerful, privacy-focused alternative to cloud-based AI while maintaining full compatibility with SOFIA's tool ecosystem and user interfaces.
