import gradio as gr
from ollama import chat
from chat_brain import load_config, ChatBrain

INITIAL_MESSAGES, TOOLS_SPEC = load_config("tools.yaml")
messages = INITIAL_MESSAGES.copy()
tools = TOOLS_SPEC.copy()
brain = ChatBrain(chat)

def respond(msg, _):
    text  = msg.get("text", "") if isinstance(msg, dict) else str(msg)
    files = msg.get("files", []) if isinstance(msg, dict) else []
    entry = {"role": "user", "content": text}
    if files:
        entry["images"] = files
    messages.append(entry)

    init_content = ""
    stream = chat("sofia2", messages=messages, tools=tools, stream=True)

    for chunk in stream:
        content = chunk["message"].get("content", "")
        init_content += content
        yield gr.ChatMessage(
            role="assistant",
            content=init_content,
            metadata= None
        )

        if chunk["message"].get("tool_calls"):
            yield gr.ChatMessage(
                role = "assistant",
                content = "I'll call a tool for this!"
            )
            brain.execute_tool_calls(chunk, messages)
            resumed = chat("sofia2", messages=messages, tools=tools, stream=True)
            for resumed_chunk in resumed:
                tool_content = resumed_chunk["message"].get("content", "")
                init_content += tool_content
                metaData = {"title": "🛠️ Used tool"}
                yield gr.ChatMessage(
                    role="assistant",
                    content=init_content,
                    metadata= metaData
                )
            break

    messages.append({"role": "assistant", "content": init_content})

with gr.Blocks() as demo:
    chatbot = gr.Chatbot(messages, type="messages")
    gr.Radio(["Chat", "Agent"])
    gr.ChatInterface(
        fn=respond,
        chatbot=chatbot,
        type="messages",
        multimodal=True,
        title="🤖 Sofia Chat (Vision + Tooling)"
    )

demo.launch(server_name="0.0.0.0", server_port=7860)
