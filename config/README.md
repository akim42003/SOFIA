# SOFIA Configuration System

## Overview

The SOFIA configuration system has tool definitions split into separate files by category.

## Structure

```
config/
├── tools.yaml          # Main configuration with messages and system prompts
├── load_tools.py        # Tool loader that combines all files
├── README.md           # This file
└── tools/              # Individual tool category files
    ├── system.yaml     # System operations (file I/O, commands)
    ├── gmail.yaml      # Gmail integration tools
    ├── calendar.yaml   # Calendar management tools
    ├── desktop.yaml    # Desktop automation tools
    └── conversation.yaml # Conversation management tools
```

## Tool Categories

### System Tools (`tools/system.yaml`)
- `save_file` - Write content to files
- `read_file` - Read content from files
- `execute_command` - Execute terminal commands
- `reset_google_cred` - Reset Google OAuth credentials

### Gmail Tools (`tools/gmail.yaml`)
- `gmail_search_emails` - Search emails by criteria
- `gmail_fetch_emails` - Fetch emails with filters
- `gmail_send_emails` - Send emails, replies, forwards

### Calendar Tools (`tools/calendar.yaml`)
- `calendar_list_events` - List upcoming events
- `calendar_create_event` - Create new events
- `calendar_search_events` - Search events by text
- `calendar_delete_event` - Delete events by ID

### Desktop Tools (`tools/desktop.yaml`)
- `take_screenshot` - Capture desktop screenshots
- `move_mouse` - Move mouse cursor
- `click_mouse` - Click mouse buttons
- `drag_mouse` - Drag mouse operations
- `type_text` - Type text input
- `press_key` - Press keyboard keys
- `hotkey` - Execute keyboard shortcuts

### Conversation Tools (`tools/conversation.yaml`)
- `save_conversation` - Save and summarize conversations

## Adding New Tools

1. Choose the appropriate category file or create a new one
2. Add your tool definition following the existing format:

```yaml
tools:
  - function:
      description: "Tool description here"
      name: tool_name
      parameters:
        properties:
          param1:
            description: "Parameter description"
            type: string
        required:
          - param1
        type: object
    type: function
```

3. Test with: `python config/load_tools.py`

## Usage

The system automatically loads all tools from the category files when SOFIA starts. No changes needed to existing code - it uses the same `load_config()` function with automatic fallback to the monolithic format if needed.

## Benefits

- **Maintainability**: Easier to find and modify specific tools
- **Readability**: Smaller, focused files are easier to read
- **Extensibility**: Easy to add new tool categories
- **Validation**: Built-in validation and error checking
- **Backward Compatibility**: Automatic fallback to old format

## Testing

Run the validation script to check configuration:

```bash
python config/load_tools.py
```

This will show:
- Number of tools loaded from each file
- Complete list of available tools
- Any validation errors
