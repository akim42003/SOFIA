"""Memory management for SOFIA web interface chat history."""

# Memory management settings
MAX_SCREENSHOT_MESSAGES = 5  # Keep max 5 screenshot messages in memory
MAX_TOTAL_MESSAGES = 50      # Keep max 50 total messages in memory


def cleanup_old_messages(messages):
    """Clean up old messages to prevent memory accumulation"""
    # First, clean up excess screenshot messages
    screenshot_count = 0
    cleaned_messages = []

    # Process messages in reverse order to keep the most recent screenshots
    for msg in reversed(messages):
        if msg.get('role') == 'assistant' and msg.get('images'):
            if screenshot_count < MAX_SCREENSHOT_MESSAGES:
                cleaned_messages.insert(0, msg)
                screenshot_count += 1
            # Skip older screenshot messages
        elif msg.get('role') == 'tool' and msg.get('name') == 'take_screenshot':
            if screenshot_count < MAX_SCREENSHOT_MESSAGES:
                cleaned_messages.insert(0, msg)
                # Don't increment counter for tool messages, only for image messages
            # Skip older screenshot tool messages
        else:
            cleaned_messages.insert(0, msg)

    # Then, limit total message count
    if len(cleaned_messages) > MAX_TOTAL_MESSAGES:
        # Keep the most recent messages
        cleaned_messages = cleaned_messages[-MAX_TOTAL_MESSAGES:]

    return cleaned_messages


def cleanup_screenshot_resources():
    """Clean up screenshot files and resources without touching conversation messages"""
    try:
        # Clean up old screenshot files
        from sofia.core.tools.desktop import cleanup_old_screenshots
        cleanup_old_screenshots()

        # Force garbage collection to prevent memory accumulation
        import gc
        gc.collect()

        print("Screenshot resources cleaned up")

    except Exception as e:
        print(f"Warning: Screenshot resource cleanup failed: {e}")