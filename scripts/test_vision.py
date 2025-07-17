from ollama import ChatResponse, chat
import yaml
import json
from pathlib import Path

def load_config(config_file='eyes.yaml'):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('messages', [])

# Load config from YAML file.
messages = load_config()

class LLM_EYES:
    def __init__(self, chat_func):
        self.chat = chat_func
    
    def _get_user_first_name(self):
        """Get user's first name from config file"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "user_config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    full_name = user_config.get("user_name", "User")
                    return full_name.split()[0] if full_name else "User"
        except Exception:
            pass
        return "User"

    def continuous_chat(self, messages):
        user_name = self._get_user_first_name()
        user_input = input(f"{user_name}: ")
        messages.append({"role": "user", "content": user_input})
        response: ChatResponse = self.chat(
            "sofia2",
            messages=messages,
        )
        return response.message.content, user_input
    def initialize_chat(self, messages):
        user_name = self._get_user_first_name()
        print(f"SOFIA Vision: Hi {user_name}! How can I help you?")
        while True:
            try:
                response_text, _ = self.continuous_chat(messages)
                if not response_text:
                    response_text = "I'm not sure how to respond."
                print("SOFIA Vision: " + response_text)
            except KeyboardInterrupt:
                print("\nSOFIA Vision: Goodbye!")
                break

def main():
    chat_brain_instance = LLM_EYES(chat)
    chat_brain_instance.initialize_chat(messages)

if __name__ == "__main__":
    main()
