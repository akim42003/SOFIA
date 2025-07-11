import ollama
from PyQt6.QtCore import QThread, pyqtSignal
from sofia.core.openai_brain import OpenAIChatBrain


class AnalysisThread(QThread):
    """Thread for AI analysis and tool execution"""
    response_received = pyqtSignal(str)
    streaming_chunk = pyqtSignal(str)  # New signal for streaming chunks
    streaming_finished = pyqtSignal(str)  # New signal when streaming is complete

    def __init__(self, prompt, image_path=None, brain=None, chat_messages=None, tools=None):
        super().__init__()
        self.prompt = prompt
        self.image_path = image_path
        self.brain = brain
        self.chat_messages = chat_messages or []
        self.tools = tools or []

    def run(self):
        try:
            # Build message with proper context
            user_message = {
                "role": "user",
                "content": self.prompt
            }

            if self.image_path:
                user_message["images"] = [self.image_path]

            # Add user message to conversation history
            messages = self.chat_messages.copy()
            messages.append(user_message)

            # Check if we're using OpenAI brain
            if isinstance(self.brain, OpenAIChatBrain):
                # Use OpenAI brain's chat method
                try:
                    # Convert messages and tools to OpenAI format
                    from sofia.core.openai_brain import convert_messages_to_openai_format, convert_tools_to_openai_format
                    openai_messages = convert_messages_to_openai_format(messages)
                    openai_tools = convert_tools_to_openai_format(self.tools)
                    
                    # Make API call with streaming
                    response = self.brain.client.chat.completions.create(
                        model=self.brain.model,
                        messages=openai_messages,
                        tools=openai_tools if openai_tools else None,
                        stream=True
                    )
                    
                    full_content = ""
                    tool_calls = []
                    
                    for chunk in response:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            full_content += delta.content
                            self.streaming_chunk.emit(delta.content)
                        
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
                    
                    # Process tool calls if any
                    if tool_calls:
                        # Add assistant message with tool calls
                        messages.append({
                            "role": "assistant",
                            "content": full_content or "",
                            "tool_calls": tool_calls
                        })
                        
                        # Execute tools - convert dicts to proper objects
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
                        
                        self.brain.execute_tool_calls(tool_objects, messages)
                        
                        # Get final response after tool execution
                        final_messages = convert_messages_to_openai_format(messages)
                        final_response = self.brain.client.chat.completions.create(
                            model=self.brain.model,
                            messages=final_messages,
                            tools=openai_tools if openai_tools else None,
                            stream=True
                        )
                        
                        for chunk in final_response:
                            delta = chunk.choices[0].delta
                            if delta.content:
                                full_content += delta.content
                                self.streaming_chunk.emit(delta.content)
                        
                        # Emit complete response when done
                        self.streaming_finished.emit(full_content)
                    else:
                        # No tool calls, just emit the complete response
                        self.streaming_finished.emit(full_content)
                    
                except Exception as e:
                    self.response_received.emit(f"OpenAI Error: {str(e)}")
                    
            else:
                # Use Ollama brain (existing logic)
                response = ""
                for chunk in ollama.chat(model="sofia2", messages=messages, tools=self.tools, stream=True):
                    if hasattr(chunk['message'], 'tool_calls') and chunk['message'].tool_calls:
                        # Execute tool calls
                        self.brain.execute_tool_calls(chunk, messages)
                    
                    content = chunk['message'].get('content', '')
                    if content:
                        response += content
                        self.streaming_chunk.emit(content)
                
                # Emit complete response when done
                self.streaming_finished.emit(response)
                        
        except Exception as e:
            self.response_received.emit(f"Error: {str(e)}")