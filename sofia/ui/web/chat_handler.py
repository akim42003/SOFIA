"""Chat response handling for SOFIA web interface."""

import gradio as gr
from sofia.core.openai_brain import OpenAIChatBrain, convert_messages_to_openai_format, convert_tools_to_openai_format
from sofia.core.brain_factory import get_brain_and_config
from .memory_manager import cleanup_old_messages, cleanup_screenshot_resources


def respond(msg, _, brain, messages, tools):
    """Handle chat responses with tool calling support"""
    text = msg.get("text", "") if isinstance(msg, dict) else str(msg)
    files = msg.get("files", []) if isinstance(msg, dict) else []
    entry = {"role": "user", "content": text}
    if files:
        entry["images"] = files
    messages.append(entry)

    # Clean up old messages before processing to manage memory
    cleaned_messages = cleanup_old_messages(messages)
    messages.clear()
    messages.extend(cleaned_messages)

    # Clean up screenshot files and resources without touching conversation messages
    cleanup_screenshot_resources()

    # Debug: Ensure tools are available
    if not tools:
        print("WARNING: No tools loaded!")
        # Reload tools if empty
        _, _, tools_spec = get_brain_and_config()
        tools.clear()
        tools.extend(tools_spec)

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

                # Continue to next iteration for follow-up response
                full_response += "\n\n"
                continue

        # If no tool calls, we're done
        if not has_tool_calls:
            if init_content:
                messages.append({"role": "assistant", "content": init_content})
            break

    return