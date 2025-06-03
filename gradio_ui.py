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

    assistant_prefix = ""
    stream = chat("sofia2", messages=messages, tools=tools, stream=True)

    for chunk in stream:
        delta = chunk["message"].get("content", "")
        assistant_prefix += delta
        yield gr.ChatMessage(
            role="assistant",
            content=assistant_prefix,
            metadata= None
        )

        if chunk["message"].get("tool_calls"):
            brain.execute_tool_calls(chunk, messages)
            resumed = chat("sofia2", messages=messages, tools=tools, stream=True)
            for resumed_chunk in resumed:
                delta2 = resumed_chunk["message"].get("content", "")
                assistant_prefix += delta2
                yield gr.ChatMessage(
                    role="assistant",
                    content=assistant_prefix,
                    metadata={"title": "Thinking", "status": "pending"}
                )
            break

    # After (no metadata -> plain bubble)
    yield gr.ChatMessage(
        role="assistant",
        content=assistant_prefix,
        metadata=None
    )

    messages.append({"role": "assistant", "content": assistant_prefix})

with gr.Blocks() as demo:
    chatbot = gr.Chatbot(messages, type="messages")
    gr.ChatInterface(
        fn=respond,
        chatbot=chatbot,
        type="messages",
        multimodal=True,
        title="🤖 Sofia Chat (Vision + Tooling)"
    )

demo.launch()
