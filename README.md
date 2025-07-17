# SOFIA - Sort of Functional Interactive Agent

**SOFIA** is a *sometimes* powerful AI assistant that bridges the gap between large language models and your desktop, enabling seamless automation of tasks through natural language conversations.

## Overview

### Augmented Chat System
- **Multimodal Conversations** - Chat with text and images through an intuitive Gradio interface
- **Tool-Enabled AI** - SOFIA can execute actions based on your requests, not just respond with text
- **Streaming Responses** - Real-time feedback as SOFIA processes your requests

### Desktop Automation
- **Visual Understanding** - SOFIA can see your screen and understand UI elements using advanced computer vision
- **Mouse & Keyboard Control** - Automate clicks, typing, and navigation
- **Smart Element Detection** - Powered by YOLO models and OCR for accurate UI interaction

### Gmail & Calendar Integration
- **Email Management** - Search, read, and compose emails through natural language
- **Smart Replies** - SOFIA can draft contextual responses to your emails
- **Thread Support** - Maintains conversation context when replying or forwarding
- **Calendar Management** - Create, list, search, and delete calendar events with natural language
- **Smart Time Parsing** - "Friday 6pm" automatically uses your local timezone and current month
- **Event Coordination** - Seamlessly manage meetings and appointments through conversation

### System Tools
- **File Operations** - Read, write, and manage files within the SOFIA directory
- **Command Execution** - Run system commands safely through natural language
- **Sandboxed Environment** - All operations are contained within `~/SOFIA/` for security

### Audio Interface
- **Web Audio Upload** - Upload audio files for transcription and analysis
- **Whisper Integration** - High-quality speech-to-text using OpenAI Whisper
- **Meeting Transcription** - Perfect for remote meeting notes and summaries
- **Mobile Support** - Record on phone, upload via web interface over VPN

## Getting Started

### Prerequisites
- Python 3.11+
- Conda (recommended for virtual environment)
- For local AI: Ollama installed and running with CUDA-capable GPU
- For cloud AI: OpenAI API key
- **seperate monitors for web app and computer use environment highly suggested**

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

5. **Set up Gmail & Calendar integration (optional)**
   ```bash
   # Place your Google credentials file as credentials.json in the project root
   # Run the Gmail & Calendar MCP server in a separate terminal
   python sofia_gmail.py
   # Follow OAuth flow for first-time setup
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

## Agent Features

### **Computer Vision & UI Understanding**
- **Advanced Screenshot Analysis**: Automatically captures and analyzes screen content with significant noise reduction
- **Smart UI Element Detection**: Identifies buttons, icons, text fields, and interactive elements with precise pixel coordinates
- **Region-Based Analysis (Desktop Only)**: Select specific screen areas for focused analysis
- **LLM-Optimized Vision**: Structured, clean output format specifically designed for agent comprehension
- **Intelligent File Management**: Automatic cleanup of temporary screenshot files prevents system bloat
- **Memory-Optimized Processing**: Debounce protection and message history management for sustained performance

### **Desktop Automation**
- **Reliable Mouse Control**: Validated coordinate-based clicking with error handling and position verification
- **Intelligent Keyboard Input**: Text typing with optimized timing for UI responsiveness
- **Hotkey Management**: Complex key combinations for advanced system interactions
- **Optimized Performance**: Reduced wait times and intelligent cooldowns for faster execution
- **Race Condition Prevention**: Smart debouncing prevents conflicts between manual and automatic screenshots

### **Autonomous Agent Workflow**
- **Built-in Planning**: Every task includes mandatory THINK → PLAN → EXECUTE → VERIFY workflow
- **Tool Orchestration**: Intelligent sequencing of multiple tools to complete complex tasks
- **Self-Verification**: Automatically takes screenshots and analyzes results to confirm task completion


### **Vision System Optimization**
- **Noise Filtering**: Removes irrelevant UI elements while preserving all interactive components
- **Smart Prioritization**: Organizes screen elements by importance and interactability
- **Relative Positioning**: Human-readable location descriptions (top-left, center, etc.)
- **Element Classification**: Distinguishes between text, buttons, icons, and input fields

## AI Backend Options

SOFIA now supports both local and cloud AI backends:

### **Local AI (Ollama)**
- Runs completely offline on your machine
- Requires a CUDA-capable GPU
- No API costs
- Full privacy - data never leaves your machine
- **mistral-small3.1:24b or llama4 highly suggested as the base model**

### **Cloud AI (OpenAI)**
- No GPU required - perfect for users without robust PC setups
- Access to latest GPT models (GPT-4, GPT-4o-mini)
- Requires OpenAI API key and incurs usage costs
- Faster, more accurate responses for complex tasks (especially computer use)

### **Switching Backends**
```bash
# Check current backend
python switch_backend.py status

# Switch to OpenAI (cloud)
export OPENAI_API_KEY='your-api-key'
python switch_backend.py openai

# Switch back to Ollama (local)
python switch_backend.py ollama
```

## Configuration

SOFIA's behavior and available tools are configured through:
- `config/tools.yaml` - System prompts, personality, and available tools
- `config/sofia_config.yaml` - AI backend selection and model settings

### Configuration Files

**sofia_config.yaml** - Controls AI backend:
```yaml
ai_backend: "ollama"  # or "openai"

openai:
  model: "gpt-4o"  # or any API accesible model
  # api_key: "your-key"  # Optional, can use env var

ollama:
  model: "sofia2"
```

## Security

- All file operations are sandboxed to the SOFIA directory
- Gmail & Calendar integration requires OAuth2 authentication with appropriate scopes
- Command execution is logged and can be restricted
- Sensitive credentials are stored securely using system keyrings

**Note**: SOFIA is designed for personal automation and productivity. Always ensure you understand what commands SOFIA will execute before confirming actions.

Built out of curiosity by Alex Kim.
