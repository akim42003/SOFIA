# SOFIA - Sort of Functional Interactive Agent

A sophisticated AI assistant platform that combines desktop automation, email/calendar management, and multimodal interaction capabilities. SOFIA provides a flexible, privacy-conscious solution for automating tasks through natural language conversation.

## Overview

SOFIA operates through multiple interfaces (web, desktop overlay, and MCP server) with a dual AI backend system supporting both local (Ollama) and cloud (OpenAI) models. The platform uses advanced computer vision for UI automation and integrates seamlessly with Google services while maintaining strict security boundaries.

## Key Features

- **Desktop Automation**: Computer vision-powered UI element detection using OmniParser, precise mouse/keyboard control, screenshot analysis, and sandboxed shell command execution
- **Email & Calendar Integration**: Full Gmail functionality (search, compose, reply, forward) and Google Calendar management through natural language with OAuth2 authentication
- **Local Conversation Storage**: Compacts and stores past conversations as md files for future use and reference.
- **Multimodal Processing**: Text and image chat support, audio file transcription via Whisper, real-time streaming responses, and drag-and-drop file handling
- **Flexible AI Backend**: Hot-swappable between local Ollama models (privacy-focused, offline) and OpenAI API (faster, more accurate) via Brain Factory pattern
- **Safety-First Design**: All file operations sandboxed to ~/SOFIA/ directory, parameter validation, graceful error handling, and secure API key management

## Architecture

SOFIA employs a modular architecture with three primary interfaces:

1. **Web Interface** (`sofia_web.py`): Gradio-based UI for multimodal chat and audio transcription
2. **Desktop Interface** (`sofia_desktop.py`): PyQt6 transparent overlay for seamless desktop integration
3. **MCP Server** (`sofia_gmail.py`): Model Context Protocol server for Google services

The system uses a THINK → PLAN → EXECUTE → VERIFY workflow for autonomous task completion, with concurrent tool execution and conversation memory management.

## Demo

See SOFIA's computer use capabilities in action:

[https://github.com/user-attachments/assets/sofia_demo.mp4](https://github.com/user-attachments/assets/67e84b5c-9a3d-4bb5-84c7-ee2982c2275f)

*The demo showcases SOFIA's ability to understand visual interfaces, navigate applications, and perform desktop automation tasks.*

## Getting Started

### Requirements

- Ubuntu 22.04+ (Windows/macOS support planned)
- Python 3.11+
- For computer use and local AI: CUDA enabled GPU (24gb+ recommended)
- For cloud AI: OpenAI API key
- Google credentials for email/calendar features
- Separate monitor recommended for desktop automation

### Installation

```bash
git clone https://github.com/akim42003/SOFIA.git
cd SOFIA
conda create -n sofia python=3.11
conda activate sofia
pip install -r requirements.txt

# For local AI models
ollama create sofia -f Modelfile.enhanced
```

### Google Services Setup

1. Place `credentials.json` in project root
2. Run `python sofia_gmail.py` to authenticate
3. Follow OAuth2 flow in browser

### Usage

```bash
# Web interface with audio support
python sofia_web.py      # Access at localhost:7860

# Desktop overlay interface
python sofia_desktop.py  # Transparent UI overlay

# Gmail/Calendar server
python sofia_gmail.py    # MCP server on port 3000
```

## Computer Vision & Automation

SOFIA's desktop automation leverages advanced computer vision:

- **OmniParser Integration**: YOLO-based UI element detection with Florence2/BLIP2 captioning
- **Visual Grounding**: Maps natural language descriptions to precise pixel coordinates
- **Screenshot Analysis**: Real-time screen capture and interpretation
- **Error Recovery**: Automatic retry mechanisms with visual verification

## AI Backend Options

### Local Models (Ollama)
- **Pros**: Complete privacy, offline operation, no API costs
- **Cons**: Requires CUDA GPU (8GB+ VRAM), slower inference
- **Recommended Models**: mistral-small3.1:24b, llama4, custom sofia model

### Cloud Models (OpenAI)
- **Pros**: Faster response, higher accuracy, no hardware requirements
- **Cons**: API costs, requires internet, data privacy considerations
- **Available Models**: gpt-4o, gpt-4, gpt-3.5-turbo

### Backend Management

```bash
python switch_backend.py status   # Check current backend
python switch_backend.py openai   # Switch to OpenAI
python switch_backend.py ollama   # Switch to Ollama
```

## Configuration

### Main Configuration
Edit `config/sofia_config.yaml`:

```yaml
ai_backend: "ollama"  # or "openai"
openai:
  model: "gpt-4o"
ollama:
  model: "sofia2"
```

### Tool Configuration
Customize agent behavior and available tools in `config/tools`

### User Personalization
Create `config/user_config.yaml` for personal preferences and context

## Security Considerations

- All file operations restricted to `~/SOFIA/` directory
- API keys managed via environment variables
- OAuth2 for Google service authentication
- Parameter validation on all tool invocations
- No arbitrary code execution outside sandboxed environment

## Troubleshooting

- **GPU Memory Issues**: Reduce model size or switch to CPU inference
- **OCR Performance**: Ensure CUDA is properly configured for OmniParser
- **Gmail Authentication**: Check credentials.json and OAuth2 token validity
- **Desktop Control**: Verify PyAutoGUI permissions and display configuration

Built by Alex Kim.
