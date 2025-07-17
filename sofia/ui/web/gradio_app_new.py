"""Main entry point for SOFIA web interface with refactored components."""

from sofia.core.brain_factory import get_brain_and_config, load_sofia_config
from .audio_handler import WHISPER_AVAILABLE
from .interface import create_chat_interface

# Global variables that will be initialized in create_demo()
brain = None
messages = []
tools = []
backend = "ollama"


def create_demo():
    """Create and return the Gradio demo interface"""
    # Get brain instance and configuration
    global brain, messages, tools, backend
    brain, INITIAL_MESSAGES, TOOLS_SPEC = get_brain_and_config()

    # Clean initial messages - remove any tool-related messages when starting fresh
    cleaned_messages = []
    for msg in INITIAL_MESSAGES:
        if msg['role'] not in ['tool'] and not (msg['role'] == 'assistant' and 'tool_calls' in msg):
            cleaned_messages.append(msg)

    messages = cleaned_messages.copy()
    tools = TOOLS_SPEC.copy()

    # Determine which backend is being used
    config = load_sofia_config()
    backend = config.get('ai_backend', 'ollama')

    # Create the interface
    return create_chat_interface(brain, messages, tools, backend)


def main():
    """Main function to launch the Gradio app"""
    demo = create_demo()

    print("Starting SOFIA web interface...")
    if WHISPER_AVAILABLE:
        print("Audio file upload available for transcription")

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        quiet=False,
    )


if __name__ == "__main__":
    main()
