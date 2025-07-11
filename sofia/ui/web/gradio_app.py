import gradio as gr
from sofia.core.brain_factory import get_brain_and_config, load_sofia_config
from sofia.core.openai_brain import OpenAIChatBrain, convert_messages_to_openai_format, convert_tools_to_openai_format
import os

# Global variables that will be initialized in create_demo()
brain = None
messages = []
tools = []
backend = "ollama"

# Memory management settings
MAX_SCREENSHOT_MESSAGES = 5  # Keep max 5 screenshot messages in memory
MAX_TOTAL_MESSAGES = 50      # Keep max 50 total messages in memory

def cleanup_old_messages():
    """Clean up old messages to prevent memory accumulation"""
    global messages
    
    # First, clean up excess screenshot messages
    screenshot_count = 0
    cleaned_messages = []
    
    # Process messages in reverse order to keep the most recent screenshots
    for msg in reversed(messages):
        if msg.get('role') == 'assistant' and msg.get('images'):
            if screenshot_count < MAX_SCREENSHOT_MESSAGES:
                cleaned_messages.insert(0, msg)
                screenshot_count += 1
            # Skip older screenshot messages
        elif msg.get('role') == 'tool' and msg.get('name') == 'take_screenshot':
            if screenshot_count < MAX_SCREENSHOT_MESSAGES:
                cleaned_messages.insert(0, msg)
                # Don't increment counter for tool messages, only for image messages
            # Skip older screenshot tool messages
        else:
            cleaned_messages.insert(0, msg)
    
    # Then, limit total message count
    if len(cleaned_messages) > MAX_TOTAL_MESSAGES:
        # Keep the most recent messages
        cleaned_messages = cleaned_messages[-MAX_TOTAL_MESSAGES:]
    
    messages = cleaned_messages


def respond(msg, _):
    global tools  # Declare global before using

    text  = msg.get("text", "") if isinstance(msg, dict) else str(msg)
    files = msg.get("files", []) if isinstance(msg, dict) else []
    entry = {"role": "user", "content": text}
    if files:
        entry["images"] = files
    messages.append(entry)
    
    # Clean up old messages before processing to manage memory
    cleanup_old_messages()

    # Debug: Ensure tools are available
    if not tools:
        print("WARNING: No tools loaded!")
        # Reload tools if empty
        _, _, tools = get_brain_and_config()

    MAX_ITERATIONS = 10  # Safety limit to prevent infinite loops
    iteration = 0
    full_response = ""

    while iteration < MAX_ITERATIONS:
        iteration += 1
        init_content = ""
        has_tool_calls = False
        tool_calls = []  # Accumulate all tool calls

        # Check if we're using OpenAI brain
        if isinstance(brain, OpenAIChatBrain):
            # Convert messages and tools to OpenAI format
            openai_messages = convert_messages_to_openai_format(messages)
            openai_tools = convert_tools_to_openai_format(tools)

            # Make API call with streaming
            try:
                stream = brain.client.chat.completions.create(
                    model=brain.model,
                    messages=openai_messages,
                    tools=openai_tools if openai_tools else None,
                    stream=True
                )

                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        init_content += delta.content
                        full_response += delta.content

                        yield gr.ChatMessage(
                            role="assistant",
                            content=full_response,
                            metadata={"iteration": iteration} if iteration > 1 else None
                        )

                    # Accumulate tool calls
                    if delta.tool_calls:
                        has_tool_calls = True
                        for tc in delta.tool_calls:
                            if tc.index >= len(tool_calls):
                                tool_calls.append({
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name if tc.function else None,
                                        "arguments": tc.function.arguments if tc.function else ""
                                    }
                                })
                            else:
                                if tc.function and tc.function.arguments:
                                    tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

                # Execute tool calls if any
                if tool_calls:
                    yield gr.ChatMessage(
                        role="assistant",
                        content=f"{full_response}\n\n🛠️ Executing {len(tool_calls)} tool(s)..."
                    )

                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": init_content or "",
                        "tool_calls": tool_calls
                    })

                    # Convert tool calls to objects and execute
                    tool_objects = []
                    for tc in tool_calls:
                        # Create a proper tool call object
                        tool_obj = type('ToolCall', (), {
                            'id': tc['id'],
                            'function': type('Function', (), {
                                'name': tc['function']['name'],
                                'arguments': tc['function']['arguments']
                            })()
                        })()
                        tool_objects.append(tool_obj)

                    brain.execute_tool_calls(tool_objects, messages)

                    # OpenAI brain handles screenshot processing automatically
                    # No need for additional screenshot logic here

                    # Continue to next iteration for follow-up response
                    full_response += "\n\n"
                    continue

            except Exception as e:
                yield gr.ChatMessage(
                    role="assistant",
                    content=f"OpenAI Error: {str(e)}"
                )
                break

        else:
            # Use Ollama brain (existing logic)
            from ollama import chat
            stream = chat("sofia2", messages=messages, tools=tools, stream=True)

            for chunk in stream:
                content = chunk["message"].get("content", "")
                init_content += content
                full_response += content


                yield gr.ChatMessage(
                    role="assistant",
                    content=full_response,
                    metadata={"iteration": iteration} if iteration > 1 else None
                )

                # Accumulate tool calls instead of executing immediately
                if chunk["message"].get("tool_calls"):
                    has_tool_calls = True
                    tool_calls.extend(chunk["message"]["tool_calls"])

            # Execute all accumulated tool calls at once (in parallel)
            if tool_calls:
                yield gr.ChatMessage(
                    role="assistant",
                    content=f"{full_response}\n\n🛠️ Executing {len(tool_calls)} tool(s)..."
                )

                # Create a response-like object with all accumulated tool calls
                class MockResponse:
                    class Message:
                        def __init__(self, tool_calls):
                            self.tool_calls = tool_calls

                    def __init__(self, tool_calls):
                        self.message = self.Message(tool_calls)

                combined_response = MockResponse(tool_calls)
                brain.execute_tool_calls(combined_response, messages)

                # Check if any desktop-related tools were called and automatically take a screenshot
                desktop_tools = {"move_mouse", "click_mouse", "drag_mouse", "type_text", "press_key", "hotkey"}
                has_desktop_actions = any(tool.function.name in desktop_tools for tool in tool_calls)
                has_explicit_screenshot = any(tool.function.name == "take_screenshot" for tool in tool_calls)

                if has_desktop_actions and not has_explicit_screenshot:
                    try:
                        # Automatically take a screenshot for verification only if none was explicitly requested
                        screenshot_result = brain.available_functions["take_screenshot"]()
                        
                        # Only proceed if screenshot was successful and not debounced
                        if screenshot_result.get("status") != "error" and screenshot_result.get("status") != "debounced":
                            messages.append({
                                "role": "tool",
                                "content": str(screenshot_result),
                                "name": "take_screenshot"
                            })

                            # Process screenshot if successful
                            path = screenshot_result.get("path")
                            if path and os.path.exists(path):
                                # For Ollama, skip OmniParser processing to avoid failures
                                # Just add the screenshot without detailed analysis
                                messages.append({
                                    "role": "assistant",
                                    "content": "Desktop action completed - screenshot taken for verification.",
                                    "images": [path]
                                })
                        elif screenshot_result.get("status") == "debounced":
                            # Screenshot was debounced, mention this without adding duplicate
                            messages.append({
                                "role": "assistant",
                                "content": "Desktop action completed - recent screenshot available."
                            })
                            
                    except Exception as screenshot_error:
                        print(f"Error taking screenshot: {screenshot_error}")

                # Continue to next iteration for follow-up response
                full_response += "\n\n"
                continue

        # If no tool calls, we're done
        if not has_tool_calls:
            if init_content:
                messages.append({"role": "assistant", "content": init_content})
            break

    return


def create_demo():
    """Create and return the Gradio demo interface"""
    # Get brain instance and configuration
    global brain, messages, tools, backend
    brain, INITIAL_MESSAGES, TOOLS_SPEC = get_brain_and_config()

    # Clean initial messages - remove any tool-related messages when starting fresh
    cleaned_messages = []
    for msg in INITIAL_MESSAGES:
        if msg['role'] not in ['tool'] and not (msg['role'] == 'assistant' and 'tool_calls' in msg):
            cleaned_messages.append(msg)

    messages = cleaned_messages.copy()
    tools = TOOLS_SPEC.copy()

    # Determine which backend is being used
    config = load_sofia_config()
    backend = config.get('ai_backend', 'ollama')


    demo = gr.ChatInterface(
        fn=respond,
        multimodal=True,
        title=f"SOFIA Assistant ({backend.upper()} Backend)",
        description=f"Sort of Functional Interactive Agent - Running on {backend.upper()}",
        examples=[
            {"text": "Show me the current time"},
            {"text": "Take a screenshot and describe what you see"},
            {"text": "Check my recent emails"},
        ],
        cache_examples=False,
    )

    return demo


def main():
    """Main function to launch the Gradio app"""
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        quiet=False,
    )


if __name__ == "__main__":
    main()
