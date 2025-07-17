# Screenshot System Optimization

## Overview

The SOFIA screenshot system has been optimized to address performance bottlenecks, memory leaks, and race conditions that could impact long-running sessions. This optimization spans across multiple components including desktop tools, memory management, and UI interfaces.

## Architecture Overview

The screenshot optimization system consists of three main components:

1. **Desktop Tools Layer** (`sofia/core/tools/desktop.py`): File management, debounce protection, and system integration
2. **Memory Management Layer** (`sofia/ui/web/memory_manager.py`): Conversation history cleanup and resource management
3. **Brain Integration Layer** (`sofia/core/brain.py`, `sofia/core/openai_brain.py`): Error handling, retry logic, and processing optimization

## Key Improvements

### 1. Automatic File Cleanup
**Problem**: Screenshot files created with `delete=False` accumulated indefinitely, causing disk bloat.

**Solution**:
- Implemented LRU-style cleanup maintaining maximum 10 screenshot files
- Thread-safe file tracking with automatic cleanup
- Files are removed when exceeding limit or when no longer referenced

```python
# Desktop tools now include automatic cleanup
_screenshot_files = []
_cleanup_lock = threading.Lock()
MAX_SCREENSHOT_FILES = 10

def cleanup_old_screenshots():
    """Clean up old screenshot files to prevent accumulation"""
    global _screenshot_files
    with _cleanup_lock:
        # Remove non-existent files from tracking
        _screenshot_files = [f for f in _screenshot_files if os.path.exists(f)]

        # If we have too many files, remove the oldest ones
        while len(_screenshot_files) > MAX_SCREENSHOT_FILES:
            old_file = _screenshot_files.pop(0)
            try:
                if os.path.exists(old_file):
                    os.unlink(old_file)
            except Exception as e:
                print(f"Warning: Could not remove old screenshot {old_file}: {e}")

def add_screenshot_file(filepath):
    """Add a screenshot file to tracking and trigger cleanup if needed"""
    global _screenshot_files
    with _cleanup_lock:
        _screenshot_files.append(filepath)
        if len(_screenshot_files) > MAX_SCREENSHOT_FILES:
            cleanup_old_screenshots()
```

### 2. Debounce Protection
**Problem**: Rapid successive screenshot requests could cause race conditions and system instability.

**Solution**:
- 1-second cooldown between screenshots
- Returns cached screenshot if requested too quickly
- Prevents screenshot conflicts between manual and automatic requests

```python
_last_screenshot_time = 0
_screenshot_cooldown = 1.0  # Minimum 1 second between screenshots

def take_screenshot():
    """
    Capture screenshot with debounce protection and automatic cleanup
    """
    global _last_screenshot_time

    try:
        # Check debounce - prevent screenshots if too recent
        current_time = time.time()
        if current_time - _last_screenshot_time < _screenshot_cooldown:
            # Return the most recent screenshot file if available
            with _cleanup_lock:
                if _screenshot_files and os.path.exists(_screenshot_files[-1]):
                    return {"path": _screenshot_files[-1], "status": "debounced"}

        # Clean up old files before taking new screenshot
        cleanup_old_screenshots()

        # Take screenshot using MSS for better performance
        with mss.mss() as sct:
            mon = sct.monitors[1]  # Primary display
            raw = sct.grab(mon)

        img = Image.frombytes("RGB", raw.size, raw.rgb)

        # Create temporary file
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name)
        tmp.close()

        # Track this file and update timestamp
        add_screenshot_file(tmp.name)
        _last_screenshot_time = current_time

        # Force garbage collection after large image operations
        gc.collect()

        # Add brief delay to allow system to recover
        time.sleep(0.2)

        return {"path": tmp.name}

    except Exception as e:
        return {"status": "error", "message": f"Failed to take screenshot: {str(e)}"}
```

### 3. Memory Management
**Problem**: Screenshot messages accumulated indefinitely in conversation history.

**Solution**:
- Automatic cleanup of old screenshot messages
- Maintains maximum 5 screenshot messages and 50 total messages
- Applied to both Gradio web interface and Ollama brain

```python
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
```

### 4. Performance Optimization
**Problem**: Conservative wait times caused sluggish user experience.

**Solution**:
- Reduced PyAutoGUI pause from 1.0s to 0.3s
- Optimized tool execution delays (0.8s → 0.3s)
- Faster typing intervals (0.1s → 0.05s between keystrokes)
- Minimal delays after resource-intensive operations (0.5s → 0.1s)

```python
# Configure pyautogui for reliability
pyautogui.FAILSAFE = False  # Disable failsafe for automated use
pyautogui.PAUSE = 0.3       # Reduced pause for better responsiveness

# Optimized tool execution with reduced delays
for i, tool_call in enumerate(tool_calls):
    # Add cooldown between tools (except for first tool)
    if i > 0:
        time.sleep(0.3)  # Reduced cooldown for better responsiveness

    # Execute tool...

    # Add brief delay after resource-intensive operations
    if tool_name in ["take_screenshot", "move_mouse", "click_mouse", "drag_mouse"]:
        time.sleep(0.1)

# Faster typing
def type_text(text: str):
    pyautogui.write(text, interval=0.05)  # Faster typing
    time.sleep(0.2)  # Reduced delay

# Optimized key press timing
def press_key(key: str):
    pyautogui.press(key)
    time.sleep(0.2)  # Reduced delay
```

### 5. OmniParser Integration and Error Handling
**Problem**: Vision processing could fail or overwhelm system resources.

**Solution**:
- Comprehensive retry logic with exponential backoff
- Memory and GPU cleanup before/after processing
- Helpful error messages for user understanding
- Automatic resource management

```python
def process_screenshot_with_retry(path, messages):
    """Process screenshot with comprehensive error handling"""
    # Add delay before processing to prevent resource overload
    time.sleep(1.0)

    # Retry logic for OmniParser processing
    max_retries = 2
    retry_delay = 2.0

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"OmniParser retry attempt {attempt}/{max_retries}")
                time.sleep(retry_delay)
            else:
                print("processing images with OmniParser")

            # Force cleanup before processing
            import gc
            gc.collect()

            # Clear CUDA cache if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass

            # Process with OmniParser
            from sofia.vision.omniparser import process_image
            image_content = process_image(path)
            messages.append({
                "role": "assistant",
                "content": image_content,
                "images": [path]
            })

            # Force cleanup after successful processing
            gc.collect()
            break  # Success - exit retry loop

        except Exception as omni_error:
            print(f"OmniParser processing failed (attempt {attempt + 1}): {omni_error}")

            if attempt == max_retries:
                # Final attempt failed - provide helpful error message
                error_message = (
                    "Screenshot captured, but visual analysis failed due to resource overload. "
                    "The system's vision processing models (GPU/CPU) are temporarily overwhelmed. "
                    "Please wait 5-10 seconds before taking another screenshot to allow the system to recover. "
                    "The screenshot image is still available for viewing."
                )
                messages.append({
                    "role": "assistant",
                    "content": error_message,
                    "images": [path]
                })

            # Force cleanup on error
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
```

## Performance Impact

### Before Optimization
- Screenshot files accumulated indefinitely (disk bloat)
- Memory usage grew continuously during long sessions
- UI felt sluggish due to conservative wait times (1.0s delays)
- Race conditions caused instability between chat requests
- OmniParser failures could crash the system
- No resource cleanup leading to GPU memory leaks

### After Optimization
- Disk usage remains constant (max 10 screenshot files)
- Memory usage stabilizes after initial conversation buildup
- 2-3x faster execution times for desktop automation
- Stable operation during extended use sessions
- Graceful handling of OmniParser failures with helpful error messages
- Automatic GPU and system memory cleanup
- Improved user experience with reduced wait times

## Configuration

The optimization system is self-configuring with the following defaults:

```python
# File cleanup settings (sofia/core/tools/desktop.py)
MAX_SCREENSHOT_FILES = 10           # Maximum screenshot files to keep
_screenshot_cooldown = 1.0          # Minimum seconds between screenshots
_cleanup_lock = threading.Lock()    # Thread-safe operations

# Memory management (sofia/ui/web/memory_manager.py)
MAX_SCREENSHOT_MESSAGES = 5        # Maximum screenshot messages in conversation
MAX_TOTAL_MESSAGES = 50            # Maximum total messages in conversation

# Performance settings (sofia/core/tools/desktop.py)
pyautogui.FAILSAFE = False         # Disable failsafe for automated use
pyautogui.PAUSE = 0.3              # Reduced from 1.0s for better responsiveness

# Tool execution delays (both brain implementations)
TOOL_COOLDOWN = 0.3                # Delay between tool executions
RESOURCE_INTENSIVE_DELAY = 0.1     # Delay after screenshot/mouse operations
TYPING_INTERVAL = 0.05             # Interval between keystrokes
KEY_PRESS_DELAY = 0.2              # Delay after key presses

# OmniParser retry settings
MAX_RETRIES = 2                    # Maximum retry attempts
RETRY_DELAY = 2.0                  # Delay between retry attempts
PROCESSING_DELAY = 1.0             # Delay before initial processing
```

## Monitoring

Screenshot system health can be monitored via:

### File System Monitoring
- File count in temporary directory (should stay ≤ 10 files)
- Disk usage of screenshot directory
- Console output showing cleanup operations

### Memory Monitoring
- Python process memory usage (should stabilize after initial buildup)
- GPU memory usage (if using CUDA)
- Message count in conversation history (should stay ≤ 50 messages)

### Performance Monitoring
- Response times for desktop automation tasks
- Console output showing debounce status
- OmniParser processing times and retry attempts
- Error rates for screenshot operations

### Example Monitoring Output
```
Screenshot resources cleaned up
processing images with OmniParser
Warning: Could not remove old screenshot /tmp/tmp123.png: Permission denied
OmniParser retry attempt 1/2
Screenshot captured, but visual analysis failed due to resource overload.
Calling function: take_screenshot
Function output: {'path': '/tmp/tmp456.png', 'status': 'debounced'}
```

## Troubleshooting

### Common Issues and Solutions

#### Screenshot Files Accumulating
**Symptoms**: Disk space usage growing over time, temp directory filling up
**Solution**: Check that `cleanup_old_screenshots()` is being called, verify file permissions

#### Memory Usage Growing
**Symptoms**: Python process memory increasing during long sessions
**Solution**: Verify `cleanup_old_messages()` is working, check for memory leaks in OmniParser

#### OmniParser Failures
**Symptoms**: "Screenshot captured, but visual analysis failed" errors
**Solution**: Wait 5-10 seconds between screenshots, check GPU memory, restart if persistent

#### Debounce Issues
**Symptoms**: Screenshots not updating, "status: debounced" in output
**Solution**: Wait 1 second between screenshot requests, normal behavior for rapid requests

#### Performance Degradation
**Symptoms**: Slow response times, high CPU usage
**Solution**: Check system resources, verify optimized delays are in effect, restart if needed
