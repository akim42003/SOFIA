import gradio as gr
import os
import json
import yaml
from ollama import chat

from sys_tools import save_file, read_file, execute_command, reset_google_cred
from mcp_clients import fetch_gmail, gmail_search_emails, send_gmail

from chat_brain import ChatBrain, load_config

INITIAL_MESSAGES, TOOLS_SPEC = load_config("tools.yaml")

brain = ChatBrain(chat)
messages = INITIAL_MESSAGES.copy()
tools = TOOLS_SPEC.copy()

def build_user_message(user_text: str, image_path: str) -> dict:
    user_text = user_text or ""
    if image_path:
        return {
            "role": "user",
            "content": user_text,
            "images": [image_path]
        }
    else:
        return {"role": "user", "content": user_text}

def respond(user_text, image, chat_history):
    if chat_history is None:
        chat_history = []

    try:
        user_msg = build_user_message(user_text, image)
    except FileNotFoundError as e:
        chat_history.append((f"[Error] {e}", ""))
        yield chat_history, "", None
        return

    messages.append(user_msg)

    partial_reply = ""
    stream_iter = chat(
        "sofia2",
        messages=messages,
        tools=tools,
        stream=True
    )

    for chunk in stream_iter:
        new_text = chunk["message"].get("content", "")
        partial_reply += new_text

        if not chat_history or chat_history[-1][0] != user_text:
            chat_history.append((user_text, partial_reply))
        else:
            chat_history[-1] = (user_text, partial_reply)

        yield chat_history, "", None

    messages.append({"role": "assistant", "content": partial_reply})
    yield chat_history, "", None

with gr.Blocks() as demo:
    gr.Markdown("## 🤖 Sofia Chat (Vision + Tooling)")

    chatbot = gr.Chatbot(label="Sofia", height=500)

    with gr.Row():
        txt = gr.Textbox(
            label="Type your message",
            placeholder="Enter text here (or leave blank to send only an image)",
            lines=12
        )
        img = gr.Image(
            label="Drag & drop an image (optional)",
            type="filepath",
            interactive=True
        )

    send_btn = gr.Button("Send")

    send_btn.click(
        fn=respond,
        inputs=[txt, img, chatbot],
        outputs=[chatbot, txt, img],
    )
    txt.submit(
        fn=respond,
        inputs=[txt, img, chatbot],
        outputs=[chatbot, txt, img],

    )

demo.launch()
