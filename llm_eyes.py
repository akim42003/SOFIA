from ollama import ChatResponse, chat
import yaml
import json

def load_config(config_file='eyes.yaml'):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('messages', [])

# Load config from YAML file.
messages = load_config()

class LLM_EYES:
    def __init__(self, chat_func):
        self.chat = chat_func

    def continuous_chat(self, messages):
        user_input = input("Alex: ")
        messages.append({"role": "user", "content": user_input})
        response: ChatResponse = self.chat(
            "sofia-eyes",
            messages=messages,
        )
        return response.message.content, user_input
    def initialize_chat(self, messages):
        print("SOFIA Vision: Hi Alex! How can I help you?")
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
