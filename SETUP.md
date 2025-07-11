# SOFIA Setup Guide

Welcome to SOFIA! This guide will help you set up your personal AI assistant for any user.

## Quick Start

1. **Run the setup script:**
   ```bash
   python setup.py
   ```

2. **Follow the prompts** to enter your personal information:
   - Full name (e.g., "John Doe")
   - Email address (optional, for Gmail integration)
   - Display name for emails (defaults to your full name)

3. **Configure API keys:**
   ```bash
   cp .env.template .env
   # Edit .env and add your OpenAI API key
   ```

4. **Launch SOFIA:**
   ```bash
   # Web interface
   python -m sofia.ui.web.gradio_app
   
   # Desktop application
   python -m sofia.ui.desktop.main
   ```

## What the Setup Does

The setup script makes SOFIA user-agnostic by:

1. **Creating user configuration** - Saves your personal info to `~/SOFIA/config/user_config.yaml`
2. **Updating system prompts** - Replaces placeholder names with your actual name
3. **Configuring email tools** - Sets up Gmail integration with your display name
4. **Creating environment template** - Provides `.env.template` for API keys

## File Structure After Setup

```
~/SOFIA/
├── config/
│   ├── user_config.yaml     # Your personal configuration
│   ├── tools.yaml           # Updated with your name
│   ├── Modelfile.enhanced   # Updated with your name
│   └── Modelfile            # Updated with your name
├── .env.template            # Template for API keys
└── .env                     # Your actual API keys (create this)
```

## Customization

### Changing Your Information

Re-run the setup script to update your information:
```bash
python setup.py
```

### Adding API Keys

Edit the `.env` file to add your API keys:
```bash
# OpenAI API Key (required for OpenAI backend)
OPENAI_API_KEY=your_actual_api_key_here
```

### Backend Selection

Use the switch backend script to change between OpenAI and Ollama:
```bash
python switch_backend.py
```

## Troubleshooting

### Setup Script Issues

If the setup script fails:
1. Check that you have write permissions to your home directory
2. Ensure Python and PyYAML are installed
3. Run with Python 3.7+ 

### Missing Configuration

If SOFIA doesn't recognize your name:
1. Check that `~/SOFIA/config/user_config.yaml` exists
2. Verify the file contains your information
3. Re-run the setup script

### Path Issues

All file operations are automatically scoped to `~/SOFIA/` for security. If you encounter path issues:
1. Ensure files are in the correct directory structure
2. Check that the `sofia.core.tools.system.normalize_path()` function is working

## Security Notes

- All file operations are sandboxed to `~/SOFIA/`
- API keys are stored in `.env` (not committed to version control)
- Personal information is stored locally in `user_config.yaml`
- Setup script validates input and handles errors gracefully

## Next Steps

After setup, you can:
1. **Test the web interface** - Start with simple commands
2. **Configure Gmail** - Set up OAuth for email integration
3. **Try desktop automation** - Use screenshot and mouse/keyboard tools
4. **Explore tools** - Check available functions in `config/tools.yaml`

For more advanced usage, see the main README.md file.