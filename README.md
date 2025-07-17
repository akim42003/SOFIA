# SOFIA - Sort of Functional Interactive Agent

An AI assistant that can control your desktop, manage email/calendar, and handle files through conversation.

## Features

- **Desktop Control**: Takes screenshots, clicks UI elements, types text, runs commands in the shell
- **Email & Calendar**: Search/compose Gmail, manage Google Calendar events via natural language
- **File Operations**: Read/write files within the SOFIA directory
- **Audio Processing**: Upload audio files for transcription using Whisper
- **Multimodal Chat**: Text and image conversations through web interface

## Getting Started

### Requirements
- Ubuntu 22.04+
- Python 3.11+
- For local AI: Ollama with CUDA GPU
- For cloud AI: OpenAI API key (GPU highly recommended for OCR and STT performance)
- Separate monitors recommended for desktop control

### Installation

```bash
git clone https://github.com/akim42003/SOFIA.git
cd SOFIA
conda create -n sofia python=3.11
conda activate sofia
pip install -r requirements.txt
ollama create sofia -f Modelfile.enhanced
```

For Gmail/Calendar: Place `credentials.json` in project root, run `python sofia_gmail.py`

### Usage

```bash
python sofia_web.py      # Web interface at localhost:7860
python sofia_desktop.py  # Desktop interface
```

## How it Works

- **Computer Vision**: Uses OmniParser to identify UI elements with pixel coordinates
- **Automation**: Mouse/keyboard control with error handling and verification
- **Workflow**: THINK → PLAN → EXECUTE → VERIFY cycle for autonomous task completion
- **Safety**: All operations sandboxed to SOFIA directory

## AI Backend

Choose between local (Ollama) or cloud (OpenAI) models:

**Local**: Offline, private, requires CUDA GPU, use mistral-small3.1:24b or llama4
**Cloud**: Faster, more accurate, requires API key and costs money

```bash
python switch_backend.py status   # Check current backend
python switch_backend.py openai   # Switch to OpenAI
python switch_backend.py ollama   # Switch to Ollama
```

## Configuration

Edit `config/sofia_config.yaml` to change AI backend and models:

```yaml
ai_backend: "ollama"  # or "openai"
openai:
  model: "gpt-4o"
ollama:
  model: "sofia2"
```

Tools and prompts: `config/tools.yaml`

Built by Alex Kim for the love of the game.
