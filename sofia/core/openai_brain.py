import json
import os
import yaml
import base64
import time
from openai import OpenAI
from typing import List, Dict, Any, Optional
from sofia.core.tools.system import save_file, read_file, execute_command, reset_google_cred
from sofia.integrations.gmail.client import fetch_gmail, gmail_search_emails, send_gmail, calendar_list_events, calendar_create_event, calendar_search_events, calendar_delete_event
from sofia.vision.omniparser import process_image
from sofia.core.tools.desktop import (
    take_screenshot,
    move_mouse,
    click_mouse,
    drag_mouse,
    type_text,
    press_key,
    hotkey
)
from sofia.core.tools.conversation import _summarize_conversation, _save_markdown_file


def load_config(config_file='config/identity.yaml'):
    # Try using the new modular loader first
    try:
        import os
        import sys
        
        # Add config directory to path
        config_dir = os.path.dirname(config_file)
        if config_dir not in sys.path:
            sys.path.insert(0, config_dir)
        
        from load_tools import load_tools_config
        config = load_tools_config(config_dir)
        return config.get('messages', []), config.get('tools', [])
    except ImportError:
        # Fallback to original loader
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('messages', []), config.get('tools', [])


def convert_tools_to_openai_format(tools: List[Dict]) -> List[Dict]:
    """Convert Ollama tool format to OpenAI function format"""
    openai_tools = []
    for tool in tools:
        if tool.get('type') == 'function':
            func = tool.get('function', {})
            openai_tool = {
                "type": "function",
                "function": {
                    "name": func.get('name'),
                    "description": func.get('description'),
                    "parameters": func.get('parameters', {})
                }
            }
            openai_tools.append(openai_tool)
    return openai_tools


def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64 for OpenAI vision API"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None


def convert_messages_to_openai_format(messages: List[Dict]) -> List[Dict]:
    """Convert message format for OpenAI API"""
    openai_messages = []
    tool_call_tracker = {}  # Track tool_call_ids for proper message sequencing
    
    for i, msg in enumerate(messages):
        if msg['role'] == 'tool':
            tool_name = msg.get('name', 'unknown')
            
            # Check if this tool has a corresponding tool_call
            if tool_name in tool_call_tracker:
                # Normal tool response - convert to OpenAI format
                openai_msg = {
                    "role": "tool",
                    "content": msg['content'],
                    "tool_call_id": tool_call_tracker.get(tool_name)
                }
                # Remove from tracker after use
                tool_call_tracker.pop(tool_name, None)
            else:
                # Orphaned tool message (like automatic screenshots)
                if tool_name == 'take_screenshot':
                    # For automatic screenshots, check if next message is assistant with images
                    next_msg_has_images = (
                        i + 1 < len(messages) and 
                        messages[i + 1]['role'] == 'assistant' and 
                        'images' in messages[i + 1]
                    )
                    
                    if next_msg_has_images:
                        # Skip this tool message - the image will be handled by the next assistant message
                        continue
                    else:
                        # Convert to assistant message if no follow-up image message
                        openai_msg = {
                            "role": "assistant",
                            "content": f"I took a screenshot: {msg['content']}"
                        }
                else:
                    # For other orphaned tools, convert to assistant message
                    openai_msg = {
                        "role": "assistant", 
                        "content": f"Tool {tool_name} result: {msg['content']}"
                    }
            
        elif msg['role'] == 'assistant' and 'tool_calls' in msg:
            # Assistant messages with tool calls
            tool_calls_formatted = []
            for tc in msg['tool_calls']:
                if isinstance(tc, dict):
                    # Ensure proper format for tool calls
                    tool_call = {
                        "id": tc.get('id', f"call_{len(tool_calls_formatted)}"),
                        "type": "function",
                        "function": {
                            "name": tc.get('function', {}).get('name', ''),
                            "arguments": tc.get('function', {}).get('arguments', '{}')
                        }
                    }
                    tool_calls_formatted.append(tool_call)
                    # Track the tool call ID for matching with tool responses
                    tool_name = tool_call['function']['name']
                    tool_call_tracker[tool_name] = tool_call['id']
                    
            openai_msg = {
                "role": "assistant",
                "content": msg.get('content', ''),
                "tool_calls": tool_calls_formatted
            }
        else:
            # Regular messages
            # Handle images if present
            if 'images' in msg and msg['images']:
                # OpenAI only allows images in user messages, not assistant messages
                if msg['role'] == 'user':
                    # Use OpenAI vision API format for user messages
                    content_parts = []
                    
                    # Add text content
                    if msg['content']:
                        content_parts.append({
                            "type": "text",
                            "text": msg['content']
                        })
                    
                    # Add images
                    for image_path in msg['images']:
                        if os.path.exists(image_path):
                            base64_image = encode_image_to_base64(image_path)
                            if base64_image:
                                # Determine image format
                                image_format = "png"
                                if image_path.lower().endswith(('.jpg', '.jpeg')):
                                    image_format = "jpeg"
                                elif image_path.lower().endswith('.webp'):
                                    image_format = "webp"
                                
                                content_parts.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/{image_format};base64,{base64_image}",
                                        "detail": "high"  # Use high detail for better analysis
                                    }
                                })
                            else:
                                # Fallback if image encoding fails
                                content_parts.append({
                                    "type": "text", 
                                    "text": f"[Image could not be loaded: {image_path}]"
                                })
                        else:
                            content_parts.append({
                                "type": "text",
                                "text": f"[Image not found: {image_path}]"
                            })
                    
                    openai_msg = {
                        "role": "user",
                        "content": content_parts
                    }
                else:
                    # For assistant messages with images, convert to user message
                    # This handles cases like automatic screenshot analysis
                    content_parts = []
                    
                    # Add text content with indication it was originally an assistant message
                    assistant_content = msg['content']
                    content_parts.append({
                        "type": "text",
                        "text": f"[System analysis: {assistant_content}]"
                    })
                    
                    # Add images
                    for image_path in msg['images']:
                        if os.path.exists(image_path):
                            base64_image = encode_image_to_base64(image_path)
                            if base64_image:
                                # Determine image format
                                image_format = "png"
                                if image_path.lower().endswith(('.jpg', '.jpeg')):
                                    image_format = "jpeg"
                                elif image_path.lower().endswith('.webp'):
                                    image_format = "webp"
                                
                                content_parts.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/{image_format};base64,{base64_image}",
                                        "detail": "high"
                                    }
                                })
                    
                    openai_msg = {
                        "role": "user",
                        "content": content_parts
                    }
            else:
                # Text-only message
                openai_msg = {
                    "role": msg['role'],
                    "content": msg['content']
                }
        
        openai_messages.append(openai_msg)
    
    return openai_messages


def load_env_file(env_file='.env'):
    """Load environment variables from .env file"""
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value
    return env_vars


class OpenAIChatBrain:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        # Try to get API key from multiple sources
        self.api_key = api_key
        if not self.api_key:
            # Try .env file
            env_vars = load_env_file()
            self.api_key = env_vars.get("OPENAI_API_KEY")
        if not self.api_key:
            # Try environment variable
            self.api_key = os.getenv("OPENAI_API_KEY")
            
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set it in:\n"
                "1. .env file: OPENAI_API_KEY=your-key\n"
                "2. Pass api_key parameter\n"
                "3. Environment variable: export OPENAI_API_KEY='your-key'"
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.available_functions = {
            "save_file": save_file,
            "read_file": read_file,
            "execute_command": execute_command,
            "gmail_search_emails": gmail_search_emails,
            "gmail_fetch_emails": fetch_gmail,
            "gmail_send_emails": send_gmail,
            "calendar_list_events": calendar_list_events,
            "calendar_create_event": calendar_create_event,
            "calendar_search_events": calendar_search_events,
            "calendar_delete_event": calendar_delete_event,
            "reset_google_cred": reset_google_cred,
            "take_screenshot": take_screenshot,
            "move_mouse": move_mouse,
            "click_mouse": click_mouse,
            "drag_mouse": drag_mouse,
            "type_text": type_text,
            "press_key": press_key,
            "hotkey": hotkey,
            "save_conversation": self._save_conversation_wrapper,
        }
        
        # Store current messages for conversation saving
        self._current_messages = []

    def _save_conversation_wrapper(self, title: str = None, include_tools: bool = False) -> Dict:
        """
        Wrapper for saving conversation that has access to current messages
        
        Args:
            title: Optional title for the conversation
            include_tools: Whether to include tool call details in the summary
            
        Returns:
            Dict with status and file path
        """
        try:
            if not self._current_messages:
                return {
                    "status": "error",
                    "message": "No conversation found to save"
                }
            
            # Summarize the conversation
            summary = _summarize_conversation(self._current_messages, self.client, self.model)
            
            # Save as markdown file
            file_path = _save_markdown_file(summary, title)
            
            return {
                "status": "success",
                "message": f"Conversation saved successfully",
                "file_path": file_path,
                "summary_length": len(summary.split())
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to save conversation: {str(e)}"
            }

    def execute_tool_calls(self, tool_calls, messages):
        """Execute tool calls from OpenAI response"""
        executed = False
        
        # Update current messages reference for conversation saving
        self._current_messages = messages
        
        for i, tool_call in enumerate(tool_calls):
            # Add cooldown between tools (except for first tool)
            if i > 0:
                time.sleep(0.3)  # Reduced cooldown for better responsiveness
            
            tool_name = tool_call.function.name
            tool_call_id = tool_call.id
            
            try:
                args = json.loads(tool_call.function.arguments)
            except Exception as e:
                print(f"Error parsing arguments: {e}")
                args = {}

            if func := self.available_functions.get(tool_name):
                try:
                    output = func(**args)
                    print(f"Calling function: {tool_name}")
                    print("Arguments:", args)
                    print("Function output:", output)
                    
                    # Add tool response with proper tool_call_id for OpenAI
                    messages.append({
                        "role": "tool",
                        "content": str(output),
                        "tool_call_id": tool_call_id,
                        "name": tool_name  # Keep for compatibility
                    })
                    executed = True
                    
                    # Add brief delay after resource-intensive operations
                    if tool_name in ["take_screenshot", "move_mouse", "click_mouse", "drag_mouse"]:
                        time.sleep(0.1)
                    
                    # Handle screenshot processing with delays, retries, and helpful error messages
                    if tool_name == "take_screenshot":
                        path = output.get("path")
                        if path and os.path.exists(path):
                            # Add delay before processing to prevent resource overload
                            time.sleep(1.0)
                            
                            # Retry logic for OmniParser processing
                            max_retries = 2
                            retry_delay = 2.0
                            
                            for attempt in range(max_retries + 1):
                                try:
                                    if attempt > 0:
                                        print(f"OmniParser retry attempt {attempt}/{max_retries}")
                                        time.sleep(retry_delay)
                                    else:
                                        print("processing images with OmniParser")
                                    
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
                                        "role": "assistant",
                                        "content": image_content,
                                        "images": [path]
                                    })
                                    
                                    # Force cleanup after successful processing
                                    gc.collect()
                                    break  # Success - exit retry loop
                                    
                                except Exception as omni_error:
                                    print(f"OmniParser processing failed (attempt {attempt + 1}): {omni_error}")
                                    
                                    if attempt == max_retries:
                                        # Final attempt failed - provide helpful error message
                                        error_message = (
                                            "Screenshot captured, but visual analysis failed due to resource overload. "
                                            "The system's vision processing models (GPU/CPU) are temporarily overwhelmed. "
                                            "Please wait 5-10 seconds before taking another screenshot to allow the system to recover. "
                                            "The screenshot image is still available for viewing."
                                        )
                                        messages.append({
                                            "role": "assistant",
                                            "content": error_message,
                                            "images": [path]
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
                except Exception as e:
                    print(f"Error calling function: {e}")
                    messages.append({
                        "role": "tool",
                        "content": f"Error calling {tool_name}: {e}",
                        "tool_call_id": tool_call_id,
                        "name": tool_name
                    })
            else:
                print(f"Function {tool_name} not found")
                messages.append({
                    "role": "tool",
                    "content": f"Function {tool_name} not found",
                    "tool_call_id": tool_call_id,
                    "name": tool_name
                })
        
        return executed

    def continuous_chat(self, messages, tools, stream=False):
        """Handle a single chat interaction with user input and tool execution"""
        user_input = input("Alex: ")
        messages.append({"role": "user", "content": user_input})
        
        # Update current messages reference for conversation saving
        self._current_messages = messages
        
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
            # Handle streaming response
            full_content = ""
            tool_calls = []
            
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_content += delta.content
                    print(delta.content, end='', flush=True)
                
                if delta.tool_calls:
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
            
            print()  # New line after streaming
            
            # Process tool calls if any
            if tool_calls:
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": full_content or "",
                    "tool_calls": tool_calls
                })
                
                # Execute tools
                tool_executed = self.execute_tool_calls(
                    [type('obj', (object,), tc) for tc in tool_calls],  # Convert dict to object
                    messages
                )
                
                if tool_executed:
                    # Get final response after tool execution
                    final_response_text, _ = self.continuous_chat_no_input(messages, tools, stream=True)
                    return final_response_text, user_input
            else:
                messages.append({"role": "assistant", "content": full_content})
                return full_content, user_input
        else:
            # Non-streaming response
            response_message = response.choices[0].message
            
            if response_message.tool_calls:
                # Add assistant message with tool calls
                tool_calls_data = []
                for tc in response_message.tool_calls:
                    tool_calls_data.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                
                messages.append({
                    "role": "assistant",
                    "content": response_message.content or "",
                    "tool_calls": tool_calls_data
                })
                
                tool_executed = self.execute_tool_calls(response_message.tool_calls, messages)
                
                if tool_executed:
                    # Get final response after tool execution
                    final_response_text, _ = self.continuous_chat_no_input(messages, tools, stream=stream)
                    return final_response_text, user_input
            
            messages.append({"role": "assistant", "content": response_message.content})
            return response_message.content, user_input

    def continuous_chat_no_input(self, messages, tools, stream=False):
        """Continue chat without user input (for tool response handling)"""
        # Update current messages reference for conversation saving
        self._current_messages = messages
        
        openai_messages = convert_messages_to_openai_format(messages)
        openai_tools = convert_tools_to_openai_format(tools)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools if openai_tools else None,
            stream=stream
        )
        
        if stream:
            full_content = ""
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_content += delta.content
            
            messages.append({"role": "assistant", "content": full_content})
            return full_content, None
        else:
            content = response.choices[0].message.content
            messages.append({"role": "assistant", "content": content})
            return content, None

    def initialize_chat(self, messages, tools):
        """Main chat loop"""
        print("SOFIA: Hi Alex! How can I help you?")
        while True:
            try:
                response_text, _ = self.continuous_chat(messages, tools, stream=True)
                if not response_text:
                    response_text = "I'm not sure how to respond."
                # Response already printed in streaming mode
            except KeyboardInterrupt:
                print(messages)
                print("\nSOFIA: Goodbye!")
                break
            except Exception as e:
                print(f"\nSOFIA: An error occurred: {e}")
                print("Let me try again...")


def main():
    # Load config from YAML file
    messages, tools = load_config()
    
    # Try to create OpenAI brain instance (will check for API key from multiple sources)
    try:
        chat_brain_instance = OpenAIChatBrain()
        chat_brain_instance.initialize_chat(messages, tools)
    except ValueError as e:
        print(f"Error: {e}")
        return


if __name__ == "__main__":
    main()