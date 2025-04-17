from ollama import ChatResponse, chat
import json
import os
import yaml
import asyncio
from typing import List, Dict, Optional
from sys_tools import save_file, read_file, execute_command
from gmail_mcp import server
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport

def load_config(config_file='tools.yaml'):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('messages', []), config.get('tools', [])

# Load config from YAML file.
messages, tools = load_config()


def gmail_search_emails(
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, str]]:

    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            return await client.call_tool(
                "gmail_search_emails",
                {
                    "sender": sender,
                    "subject": subject,
                    "max_results": max_results
                }
            )
    # run the coroutine and return its result
    return asyncio.run(_call())

def fetch_gmail(
    max_results: int = 5,
    all_inbox: bool = False,
    unread_only: bool = False
) -> List[Dict[str, str]]:
    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            return await client.call_tool(
                "gmail_fetch_emails",
                {
                    "max_results":    max_results,
                    "all_inbox":    all_inbox,
                    "unread_only":    unread_only
                }
            )
    return asyncio.run(_call())


class ChatBrain:
    def __init__(self, chat_func):
        self.chat = chat_func
        self.available_functions = {
            "save_file": save_file,
            "read_file": read_file,
            "execute_command": execute_command,
            "gmail_search_emails": gmail_search_emails,
            "gmail_fetch_emails": fetch_gmail
        }

    def execute_tool_calls(self, response):
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

    def continuous_chat(self, messages):
        user_input = input("Alex: ")
        messages.append({"role": "user", "content": user_input})
        response: ChatResponse = self.chat(
            "qwen2.5",
            messages=messages,
            tools=tools
        )
        if response.message.tool_calls:
            tool_executed = self.execute_tool_calls(response)
            if tool_executed:
                # print("SOFIA: Tool executed successfully.")
                final_response: ChatResponse = self.chat("qwen2.5", messages=messages)
                messages.append({"role": "assistant", "content": final_response.message.content})
                return final_response.message.content, user_input
        messages.append({"role": "assistant", "content": response.message.content})

        return response.message.content, user_input

    def initialize_chat(self, messages):
        print("SOFIA: Hi Alex! How can I help you?")
        while True:
            try:
                response_text, _ = self.continuous_chat(messages)
                if not response_text:
                    response_text = "I'm not sure how to respond."
                print("SOFIA: " + response_text)
            except KeyboardInterrupt:
                print("\nSOFIA: Goodbye!")
                break

def main():
    chat_brain_instance = ChatBrain(chat)
    chat_brain_instance.initialize_chat(messages)

if __name__ == "__main__":
    main()
