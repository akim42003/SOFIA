# SOFIA - Smart Ollama Framework for Intelligent Automation

🤖 **SOFIA** is a powerful AI assistant that bridges the gap between large language models and your desktop, enabling seamless automation of tasks through natural language conversations.

## ✨ Features

### 🧠 Augmented Chat System
- **Multimodal Conversations** - Chat with text and images through an intuitive Gradio interface
- **Tool-Enabled AI** - SOFIA can execute actions based on your requests, not just respond with text
- **Streaming Responses** - Real-time feedback as SOFIA processes your requests

### 🖥️ Desktop Automation
- **Visual Understanding** - SOFIA can see your screen and understand UI elements using advanced computer vision
- **Mouse & Keyboard Control** - Automate clicks, typing, and navigation
- **Smart Element Detection** - Powered by YOLO models and OCR for accurate UI interaction

### 📧 Gmail Integration
- **Email Management** - Search, read, and compose emails through natural language
- **Smart Replies** - SOFIA can draft contextual responses to your emails
- **Thread Support** - Maintains conversation context when replying or forwarding

### 🛠️ System Tools
- **File Operations** - Read, write, and manage files within the SOFIA directory
- **Command Execution** - Run system commands safely through natural language
- **Sandboxed Environment** - All operations are contained within `/home/alex/SOFIA/` for security

### 🎙️ Voice Interface (Experimental)
- **Push-to-Talk** - Hands-free interaction using speech recognition
- **Natural TTS** - SOFIA responds with synthesized speech
- **Standalone Mode** - Run as a voice assistant without the web UI

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐
│   gradio_ui.py  │────▶│ chat_brain.py│
│   (Web Interface)│     │  (Core Logic) │
└─────────────────┘     └───────┬──────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
    ┌───▼────┐          ┌──────▼──────┐        ┌──────▼──────┐
    │sys_tools│          │ gui_tools   │        │ mcp_clients │
    │  (I/O)  │          │(Automation) │        │   (Gmail)   │
    └─────────┘          └──────┬──────┘        └──────┬──────┘
                                │                       │
                         ┌──────▼──────┐         ┌─────▼──────┐
                         │  OP_tool    │         │gmail_mcp.py│
                         │(OmniParser) │         │(MCP Server)│
                         └──────┬──────┘         └────────────┘
                                │
                         ┌──────▼──────┐
                         │util modules │
                         │(CV/OCR/YOLO)│
                         └─────────────┘
```

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Conda (recommended for virtual environment)
- Ollama installed and running
- CUDA-capable GPU (requires running Ollama docker daemon on GPU)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/SOFIA.git
   cd SOFIA
   ```

2. **Create a conda environment**
   ```bash
   conda create -n sofia python=3.11
   conda activate sofia
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Build the SOFIA model**
   ```bash
   ollama create sofia -f Modelfile
   ```

5. **Set up Gmail integration (optional)**
   ```bash
   # Run the Gmail MCP server in a separate terminal
   fastmcp run gmail_mcp.py
   ```

### Running SOFIA

#### Web Interface (Recommended)
```bash
python gradio_ui.py
```
Then open your browser to `http://localhost:7860`

#### Command Line Interface
```bash
python chat_brain.py
```


## 📁 Project Structure

```
SOFIA/
├── chat_brain.py        # Core orchestration logic
├── gradio_ui.py         # Web interface
├── tools.yaml           # Tool configurations and prompts
├── sys_tools.py         # File and command operations
├── gui_tools.py         # Desktop automation
├── OP_tool.py           # OmniParser for UI understanding
├── mcp_clients.py       # Gmail client wrapper
├── gmail_mcp.py         # Gmail MCP server
├── speaking_llm.py      # Voice interface
├── util/                # Computer vision utilities
│   ├── utils.py         # YOLO, OCR, and captioning
│   └── box_annotator.py # UI element visualization
└── Modelfile            # Ollama model configuration
```

## 🔧 Configuration

SOFIA's behavior and available tools are configured in `tools.yaml`. You can customize:
- System prompts and personality
- Available tools and their parameters
- Model settings and constraints

## 🛡️ Security Notes

- All file operations are sandboxed to the SOFIA directory
- Gmail integration requires OAuth2 authentication
- Command execution is logged and can be restricted
- Sensitive credentials are stored securely using system keyrings


## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔮 Future Roadmap

- [ ] Enhanced computer vision with Gemma 3
- [ ] Improved voice interface with advanced Whisper integration
- [ ] Automated task reasoning and planning
- [ ] Multi-monitor support
- [ ] Browser automation integration
- [ ] Plugin system for custom tools


**Note**: SOFIA is designed for personal automation and productivity. Always ensure you understand what commands SOFIA will execute before confirming actions.
