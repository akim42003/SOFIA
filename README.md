# SOFIA - Sort of Functional Interactive Agent

🤖 **SOFIA** is a *sometimes* powerful AI assistant that bridges the gap between large language models and your desktop, enabling seamless automation of tasks through natural language conversations.

## ✨ Overview

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

### 🎙️ Voice Interface (In Progress)
- **Push-to-Talk** - Hands-free interaction using speech recognition
- **Natural TTS** - SOFIA responds with synthesized speech
- **Audio Recording** - Voice input support (currently being refined)

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Conda (recommended for virtual environment)
- Ollama installed and running
- CUDA-capable GPU (requires running Ollama docker daemon on GPU)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/akim42003/SOFIA.git
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
   ollama create sofia -f Modelfile.enhanced
   ```

5. **Set up Gmail integration (optional)**
   ```bash
   # Run the Gmail MCP server in a separate terminal
   python sofia_gmail.py
   ```

### Running SOFIA

#### Web Interface (Recommended)
```bash
python sofia_web.py
```
Then open your browser to `http://localhost:7860`

#### Desktop Interface
```bash
python sofia_desktop.py       # Invisible floating assistant
```

## 🤖 Agent Features

### **Computer Vision & UI Understanding**
- **Advanced Screenshot Analysis**: Automatically captures and analyzes screen content with significant noise reduction
- **Smart UI Element Detection**: Identifies buttons, icons, text fields, and interactive elements with precise pixel coordinates
- **Region-Based Analysis (Desktop Only)**: Select specific screen areas for focused analysis
- **LLM-Optimized Vision**: Structured, clean output format specifically designed for agent comprehension

### **Desktop Automation**
- **Reliable Mouse Control**: Validated coordinate-based clicking with error handling and position verification
- **Intelligent Keyboard Input**: Text typing with time delay for UI responsiveness
- **Hotkey Management**: Complex key combinations for advanced system interactions

### **Autonomous Agent Workflow**
- **Built-in Planning**: Every task includes mandatory THINK → PLAN → EXECUTE → VERIFY workflow
- **Tool Orchestration**: Intelligent sequencing of multiple tools to complete complex tasks
- **Self-Verification**: Automatically takes screenshots and analyzes results to confirm task completion


### **Vision System Optimization**
- **Noise Filtering**: Removes irrelevant UI elements while preserving all interactive components
- **Smart Prioritization**: Organizes screen elements by importance and interactability
- **Relative Positioning**: Human-readable location descriptions (top-left, center, etc.)
- **Element Classification**: Distinguishes between text, buttons, icons, and input fields

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
