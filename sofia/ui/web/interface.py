"""Gradio interface components for SOFIA web interface."""

import gradio as gr
from .audio_handler import WHISPER_AVAILABLE, process_audio
from .chat_handler import respond


def create_chat_interface(brain, messages, tools, backend):
    """Create the main Gradio interface"""

    # Create custom interface with audio support
    with gr.Blocks(title=f"SOFIA Assistant ({backend.upper()} Backend)") as demo:
        gr.Markdown(f"# SOFIA Assistant ({backend.upper()} Backend)")
        gr.Markdown("Sort of Functional Interactive Agent - Type a message or upload audio")

        # Main chat interface
        chatbot = gr.Chatbot(label="Chat", height=500)

        # Message input (full width)
        msg_input = gr.Textbox(
            label="Message",
            placeholder="Type your message here...",
            lines=2,
            max_lines=5
        )

        with gr.Row():
            send_btn = gr.Button("Send", variant="primary")
            clear_btn = gr.Button("Clear Chat")

        # File upload for images and audio
        with gr.Row():
            file_input = gr.File(label="Upload Image", file_types=["image"])

            if WHISPER_AVAILABLE:
                audio_file_input = gr.File(
                    label="Upload Audio File",
                    file_types=[".wav", ".mp3", ".m4a", ".flac"],
                    file_count="single"
                )

        # Examples
        gr.Examples(
            examples=[
                "Show me the current time",
                "Take a screenshot and describe what you see",
                "Check my recent emails",
                "Summarize the key points from our discussion"
            ],
            inputs=[msg_input]
        )

        # Define the chat function for the interface
        def chat_fn(message, history, files):
            if not message.strip():
                return history

            # Convert files to the format expected by respond()
            if files:
                msg_dict = {"text": message, "files": [files]}
            else:
                msg_dict = {"text": message}

            # Add user message to history
            new_history = history + [(message, "")]

            # Get response generator
            response_gen = respond(msg_dict, None, brain, messages, tools)

            # Stream the response
            assistant_response = ""
            for response in response_gen:
                if hasattr(response, 'content'):
                    assistant_response = response.content
                else:
                    assistant_response = str(response)

                # Update the last message in history with current response
                yield history + [(message, assistant_response)]

            return history + [(message, assistant_response)]

        # File upload audio processing
        def process_uploaded_audio(audio_file, history):
            if not audio_file:
                return history, None

            # Extract the actual file path
            if hasattr(audio_file, 'name'):
                file_path = audio_file.name
            elif isinstance(audio_file, str):
                file_path = audio_file
            else:
                return history + [(" [Audio Upload]", "Error: Invalid file format")], None

            # Verify it's a valid file
            import os
            if not os.path.isfile(file_path):
                return history + [("[Audio Upload]", f"Error: Not a valid file")], None

            # Transcribe the audio
            transcribed_text = process_audio(file_path)
            if not transcribed_text:
                return history + [("[Audio Upload]", "Could not transcribe audio. Please try again.")], None

            # Send transcribed text to SOFIA
            msg_dict = {"text": transcribed_text}
            response_gen = respond(msg_dict, None, brain, messages, tools)

            # Stream the response
            assistant_response = ""
            for response in response_gen:
                if hasattr(response, 'content'):
                    assistant_response = response.content
                else:
                    assistant_response = str(response)

            # Return updated history and clear the file input
            return history + [(f"🎤 {transcribed_text}", assistant_response)], None

        # Event handlers
        send_btn.click(
            chat_fn,
            inputs=[msg_input, chatbot, file_input],
            outputs=[chatbot],
            show_progress=True
        ).then(
            lambda: ("", None),  # Clear inputs after sending
            outputs=[msg_input, file_input]
        )

        msg_input.submit(
            chat_fn,
            inputs=[msg_input, chatbot, file_input],
            outputs=[chatbot],
            show_progress=True
        ).then(
            lambda: ("", None),  # Clear inputs after sending
            outputs=[msg_input, file_input]
        )

        if WHISPER_AVAILABLE:
            # File upload audio handler
            audio_file_input.change(
                process_uploaded_audio,
                inputs=[audio_file_input, chatbot],
                outputs=[chatbot, audio_file_input],
                show_progress=True
            )

        clear_btn.click(
            lambda: [],
            outputs=[chatbot]
        )

    return demo
