from ollama import ChatResponse, AsyncClient, chat
import json
import os
import asyncio
import yaml
from sys_tools import save_file, read_file, execute_command, reset_google_cred
from mcp_clients import fetch_gmail, gmail_search_emails, send_gmail

def load_config(config_file='tools.yaml'):
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
            "reset_google_cred": reset_google_cred
        }

    def execute_tool_calls(self, response, messages):
        executed = False
        for tool in response.message.tool_calls:
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
                    # print("Arguments:", args)
                    # print("Function output:", output)
                    messages.append({
                        "role": "tool",
                        "content": str(output),
                        "name": tool_name,
                    })
                    executed = True
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

    async def continuous_chat(self, messages, tools):
        user_input = input("Alex: ")
        messages.append({"role": "user", "content": user_input})
        response: ChatResponse = self.chat(
            "sofia",
            messages=messages,
            tools=tools,
        )
        if response.message.tool_calls:
            tool_executed = self.execute_tool_calls(response, messages)
            if tool_executed:
                # print("SOFIA: Tool executed successfully.")
                final_response: ChatResponse = self.chat("sofia", messages=messages, tools = tools)
                messages.append({"role": "assistant", "content": final_response.message.content})
                return final_response.message.content, user_input
        messages.append({"role": "assistant", "content": response.message.content})

        return response.message.content, user_input

    async def initialize_chat(self, messages, tools):
        print("SOFIA: Hi Alex! How can I help you?")
        while True:
            try:
                response_text, _ = await self.continuous_chat(messages, tools)
                if not response_text:
                    response_text = "I'm not sure how to respond."
                print("SOFIA: " + response_text)
            except KeyboardInterrupt:
                print("\nSOFIA: Goodbye!")
                break

async def main():
    # Load config from YAML file.
    messages, tools,  = load_config()
    chat_brain_instance = ChatBrain(chat)
    await chat_brain_instance.initialize_chat(messages, tools)

if __name__ == "__main__":
    asyncio.run(main())
