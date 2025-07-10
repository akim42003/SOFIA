import gradio as gr
from ollama import chat
from sofia.core.brain import load_config, ChatBrain
import os

INITIAL_MESSAGES, TOOLS_SPEC = load_config("config/tools.yaml")
messages = INITIAL_MESSAGES.copy()
tools = TOOLS_SPEC.copy()
brain = ChatBrain(chat)

# Debug: Print tools format
print(f"DEBUG: Loaded {len(tools)} tools")
if tools and len(tools) > 0:
    print(f"DEBUG: First tool structure: {tools[0]}")


def respond(msg, _):
    global tools  # Declare global before using

    text  = msg.get("text", "") if isinstance(msg, dict) else str(msg)
    files = msg.get("files", []) if isinstance(msg, dict) else []
    entry = {"role": "user", "content": text}
    if files:
        entry["images"] = files
    messages.append(entry)

    # Debug: Ensure tools are available
    if not tools:
        print("WARNING: No tools loaded!")
        # Reload tools if empty
        _, tools = load_config("config/tools.yaml")

    MAX_ITERATIONS = 10  # Safety limit to prevent infinite loops
    iteration = 0
    full_response = ""

    while iteration < MAX_ITERATIONS:
        iteration += 1
        init_content = ""
        has_tool_calls = False
        tool_calls = []  # Accumulate all tool calls

        # Debug: Check if tools are being passed correctly
        print(f"DEBUG: Calling chat with {len(tools)} tools, streaming=True")
        stream = chat("sofia2", messages=messages, tools=tools, stream=True)

        for chunk in stream:
            content = chunk["message"].get("content", "")
            init_content += content
            full_response += content

            # Debug logging
            if content and "[TOOL_CALLS]" in content:
                print(f"DEBUG: Found [TOOL_CALLS] in content: {content}")

            yield gr.ChatMessage(
                role="assistant",
                content=full_response,
                metadata={"iteration": iteration} if iteration > 1 else None
            )

            # Accumulate tool calls instead of executing immediately
            if chunk["message"].get("tool_calls"):
                has_tool_calls = True
                tool_calls.extend(chunk["message"]["tool_calls"])
                print(f"DEBUG: Found tool_calls in chunk: {chunk['message']['tool_calls']}")

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

            if has_desktop_actions:
                # Automatically take a screenshot for verification
                screenshot_result = brain.available_functions["take_screenshot"]()
                messages.append({
                    "role": "tool",
                    "content": str(screenshot_result),
                    "name": "take_screenshot",
                })

                # Process the screenshot with vision
                if screenshot_result and isinstance(screenshot_result, dict):
                    path = screenshot_result.get("path")
                    if path and os.path.exists(path):
                        from sofia.vision.omniparser import process_image
                        image_content = process_image(path)
                        messages.append({
                            "role": "assistant",
                            "content": image_content,
                            "images": [path]
                        })

        messages.append({"role": "assistant", "content": init_content})

        # Exit if no tools were called (task likely complete)
        if not has_tool_calls:
            break

        # Add system prompt to encourage verification and continuation
        verification_prompt = """
        Tools executed successfully. For desktop actions, a screenshot has been automatically taken for verification. 
        
        ANALYZE the screenshot carefully and THINK about what you observe. 
        
        If the task is not complete, PLAN your next actions and continue with the appropriate tools. 
        
        If the task is complete and verified, provide a clear summary of what was accomplished.
        """
        
        messages.append({
            "role": "system",
            "content": verification_prompt.strip()
        })

        # Check for explicit completion indicators (but only if they also indicate verification)
        lower_content = init_content.lower()
        completion_phrases = ["task complete", "task is complete", "completed the task", "all done", "successfully completed"]
        verification_phrases = ["verified", "confirmed", "checked", "screenshot shows", "can see that", "successfully"]

        # Only break if both completion AND verification are mentioned
        has_completion = any(phrase in lower_content for phrase in completion_phrases)
        has_verification = any(phrase in lower_content for phrase in verification_phrases)

        if has_completion and has_verification:
            break

    # Add iteration info if we did multiple rounds
    if iteration > 1:
        yield gr.ChatMessage(
            role="assistant",
            content=full_response,
            metadata={"title": f"✅ Completed in {iteration} steps"}
        )

with gr.Blocks() as demo:
    chatbot = gr.Chatbot(messages, type="messages")
    #gr.Radio(["Chat", "Agent"])
    gr.ChatInterface(
        fn=respond,
        chatbot=chatbot,
        type="messages",
        multimodal=True,
        title="🤖 Sofia Chat (Vision + Tooling)",
    )

def main():
    demo.launch(server_name="0.0.0.0", server_port=7860, share = False)

if __name__ == "__main__":
    main()
