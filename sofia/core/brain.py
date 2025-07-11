from ollama import ChatResponse, chat
import json
import os
import yaml
import time
from sofia.core.tools.system import save_file, read_file, execute_command, reset_google_cred
from sofia.integrations.gmail.client import fetch_gmail, gmail_search_emails, send_gmail
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


def load_config(config_file='config/tools.yaml'):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('messages', []), config.get('tools', [])


class ChatBrain:
    def __init__(self, chat_func):
        self.chat = chat_func
        self.available_functions = {
            "save_file": save_file,
            "read_file": read_file,
            "execute_command": execute_command,
            "gmail_search_emails": gmail_search_emails,
            "gmail_fetch_emails": fetch_gmail,
            "gmail_send_emails": send_gmail,
            "reset_google_cred": reset_google_cred,
            "take_screenshot": take_screenshot,
            "move_mouse": move_mouse,
            "click_mouse": click_mouse,
            "drag_mouse": drag_mouse,
            "type_text": type_text,
            "press_key": press_key,
            "hotkey": hotkey,
        }
        
        # Memory management settings
        self.MAX_SCREENSHOT_MESSAGES = 5
        self.MAX_TOTAL_MESSAGES = 50

    def cleanup_old_messages(self, messages):
        """Clean up old messages to prevent memory accumulation"""
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

    def execute_tool_calls(self, response, messages):
        executed = False
        
        for i, tool in enumerate(response.message.tool_calls):
            # Add cooldown between tools (except for first tool)
            if i > 0:
                time.sleep(0.3)  # Reduced cooldown for better responsiveness
                
            tool_name = tool.function.name
            args = tool.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception as e:
                    print("Error parsing arguments:", e)
                    args = {}

            if func := self.available_functions.get(tool_name):
                try:
                    output = func(**args)
                    print(f"Calling function: {tool_name}")
                    print("Arguments:", args)
                    print("Function output:", output)
                    messages.append({
                        "role": "tool",
                        "content": str(output),
                        "name": tool_name,
                    })
                    executed = True
                    
                    # Add brief delay after resource-intensive operations
                    if tool_name in ["take_screenshot", "move_mouse", "click_mouse", "drag_mouse"]:
                        time.sleep(0.1)
                    
                    # Handle screenshot processing
                    if tool_name == "take_screenshot":
                        path = output.get("path")
                        if path and os.path.exists(path):
                            print("processing images")
                            image_content = process_image(path)
                            # print(image_content)
                            messages.append({
                                "role": "assistant",
                                "content": image_content,
                                "images": [path]
                            })
                except Exception as e:
                    print("Error calling function:", e)
                    messages.append({
                        "role": "tool",
                        "content": f"Error calling {tool_name}: {e}",
                        "name": tool_name,
                    })
            else:
                print("Function", tool_name, "not found")
        return executed

    def continuous_chat(self, messages, tools):
        user_input = input("Alex: ")
        messages.append({"role": "user", "content": user_input})
        
        # Clean up old messages before processing to manage memory
        cleaned_messages = self.cleanup_old_messages(messages)
        messages[:] = cleaned_messages  # Update messages list in place
        
        response: ChatResponse = self.chat(
            "sofia2",
            messages=messages,
            tools=tools,
        )
        if response.message.tool_calls:
            tool_executed = self.execute_tool_calls(response, messages)
            if tool_executed:
                # print("SOFIA: Tool executed successfully.")
                final_response: ChatResponse = self.chat("sofia2", messages=messages, tools = tools)
                messages.append({"role": "assistant", "content": final_response.message.content})
                return final_response.message.content, user_input
        messages.append({"role": "assistant", "content": response.message.content})

        return response.message.content, user_input

    def initialize_chat(self, messages, tools):
        print("SOFIA: Hi Alex! How can I help you?")
        while True:
            try:
                response_text, _ = self.continuous_chat(messages, tools)
                if not response_text:
                    response_text = "I'm not sure how to respond."
                print("SOFIA: " + response_text)
            except KeyboardInterrupt:
                print(messages)
                print("\nSOFIA: Goodbye!")
                break

def main():
    # Load config from YAML file.
    messages, tools,  = load_config()
    chat_brain_instance = ChatBrain(chat)
    chat_brain_instance.initialize_chat(messages, tools)

if __name__ == "__main__":
    main()
