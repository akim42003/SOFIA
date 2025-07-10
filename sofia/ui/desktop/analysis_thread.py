import ollama
from PyQt6.QtCore import QThread, pyqtSignal


class AnalysisThread(QThread):
    """Thread for AI analysis and tool execution"""
    response_received = pyqtSignal(str)

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

            # Use full conversation history + new message
            messages = self.chat_messages + [user_message]

            # Use brain for tool-enabled chat if available
            if self.brain:
                response = ""
                for chunk in ollama.chat(model="sofia2", messages=messages, tools=self.tools, stream=True):
                    if hasattr(chunk['message'], 'tool_calls') and chunk['message'].tool_calls:
                        # Execute tool calls
                        self.brain.execute_tool_calls(chunk, messages)
                    
                    content = chunk['message'].get('content', '')
                    if content:
                        response += content

                self.response_received.emit(response)
            else:
                # Fallback to simple chat
                response = ""
                for chunk in ollama.chat(model="sofia2", messages=messages, stream=True):
                    response += chunk['message']['content']

                self.response_received.emit(response)
        except Exception as e:
            self.response_received.emit(f"Error: {str(e)}")