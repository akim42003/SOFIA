#!/usr/bin/env python3
"""Test tool call format differences between streaming and non-streaming"""

from ollama import chat
from sofia.core.brain import load_config

# Load config
_, tools = load_config("config/tools.yaml")

# Test message that should trigger a tool call
test_messages = [
    {"role": "system", "content": "You are SOFIA, an AI assistant with tool access."},
    {"role": "user", "content": "Take a screenshot"}
]

print("=== NON-STREAMING TEST ===")
response = chat("sofia2", messages=test_messages, tools=tools, stream=False)
print(f"Has tool_calls: {bool(response.message.tool_calls)}")
if response.message.tool_calls:
    print(f"Tool calls: {response.message.tool_calls}")
if response.message.content:
    print(f"Content: {response.message.content}")

print("\n=== STREAMING TEST ===")
stream = chat("sofia2", messages=test_messages, tools=tools, stream=True)
accumulated_content = ""
found_tool_calls = False

for chunk in stream:
    if chunk["message"].get("content"):
        accumulated_content += chunk["message"]["content"]
    if chunk["message"].get("tool_calls"):
        found_tool_calls = True
        print(f"Tool calls in chunk: {chunk['message']['tool_calls']}")

print(f"Has tool_calls: {found_tool_calls}")
print(f"Accumulated content: {accumulated_content}")