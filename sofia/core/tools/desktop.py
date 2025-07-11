import pyautogui
import tempfile
import mss
import time
import os
import gc
import glob
import threading
from PIL import Image

# Configure pyautogui for reliability
pyautogui.FAILSAFE = False  # Disable failsafe for automated use
pyautogui.PAUSE = 0.3       # Reduced pause for better responsiveness

# Screenshot file management
_screenshot_files = []
_cleanup_lock = threading.Lock()
_last_screenshot_time = 0
_screenshot_cooldown = 1.0  # Minimum 1 second between screenshots
MAX_SCREENSHOT_FILES = 10  # Keep max 10 screenshot files

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

def wait_for_system_ready():
    """Wait for system to be ready for next action"""
    # Check if mouse is stable
    pos1 = pyautogui.position()
    time.sleep(0.1)
    pos2 = pyautogui.position()
    
    if pos1 != pos2:
        time.sleep(0.3)  # Mouse still moving, wait a bit

def execute_with_retry(func, *args, max_retries=3, **kwargs):
    """Execute function with automatic retry on failure"""
    for attempt in range(max_retries):
        try:
            wait_for_system_ready()
            result = func(*args, **kwargs)
            if isinstance(result, dict) and result.get("status") != "error":
                return result
        except Exception as e:
            if attempt == max_retries - 1:
                return {"status": "error", "message": f"Max retries exceeded: {str(e)}"}
        
        # Exponential backoff
        delay = 0.5 * (2 ** attempt)
        time.sleep(delay)
    
    return {"status": "error", "message": "Max retries exceeded"}

def _validate_coordinates(x: int, y: int) -> tuple[bool, str]:
    """Validate that coordinates are within screen bounds"""
    try:
        screen_width, screen_height = pyautogui.size()
        if 0 <= x <= screen_width and 0 <= y <= screen_height:
            return True, ""
        else:
            return False, f"Coordinates ({x}, {y}) outside screen bounds ({screen_width}x{screen_height})"
    except Exception as e:
        return False, f"Error validating coordinates: {e}"

def take_screenshot():
    """
    Capture just the primary monitor (monitors[1] in mss) and
    return a dict with the temporary PNG path.
    Automatically manages temporary file cleanup to prevent accumulation.
    Includes debounce mechanism to prevent rapid successive screenshots.
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
        
        with mss.mss() as sct:
            # monitors[0] = virtual desktop, monitors[1] = primary display
            mon = sct.monitors[1]                # {'left':0,'top':0,'width':..., 'height':...}
            raw = sct.grab(mon)                  # raw BGRA bytes

        img = Image.frombytes("RGB", raw.size, raw.rgb)

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name)
        tmp.close()                              # keep the file on disk
        
        # Track this file for cleanup and update timestamp
        add_screenshot_file(tmp.name)
        _last_screenshot_time = current_time
        
        # Force garbage collection after large image operations
        gc.collect()
        
        # Add delay after screenshot to allow system to recover
        time.sleep(0.2)  # Reduced delay to minimize blocking

        return {"path": tmp.name}
    except Exception as e:
        return {"status": "error", "message": f"Failed to take screenshot: {str(e)}"}

def _move_mouse_impl(x: int, y: int):
    """Internal implementation of mouse movement"""
    try:
        # Validate coordinates
        valid, error_msg = _validate_coordinates(x, y)
        if not valid:
            return {"status": "error", "message": error_msg}
        
        # Get current position for reference
        current_x, current_y = pyautogui.position()
        
        # Move mouse
        pyautogui.moveTo(x, y, duration=0.5)  # Smoother, more reliable movement
        
        # Verify movement
        time.sleep(0.3)  # Reduced delay for better responsiveness
        new_x, new_y = pyautogui.position()
        
        if abs(new_x - x) <= 2 and abs(new_y - y) <= 2:  # Allow small tolerance
            return {"status": "moved", "from": (current_x, current_y), "to": (new_x, new_y)}
        else:
            return {"status": "error", "message": f"Mouse moved to ({new_x}, {new_y}) instead of ({x}, {y})"}
            
    except Exception as e:
        return {"status": "error", "message": f"Failed to move mouse: {e}"}

def move_mouse(x: int, y: int):
    """Move mouse to specific coordinates with retry logic"""
    return execute_with_retry(_move_mouse_impl, x, y)

def _click_mouse_impl(button: str = "left"):
    """Internal implementation of mouse click"""
    try:
        # Validate button type
        valid_buttons = ["left", "right", "middle"]
        if button not in valid_buttons:
            return {"status": "error", "message": f"Invalid button '{button}'. Must be one of: {valid_buttons}"}
        
        # Get current position
        x, y = pyautogui.position()
        
        # Perform click
        pyautogui.click(button=button)
        
        # Allow UI to respond
        time.sleep(0.3)
        
        return {"status": "clicked", "button": button, "position": (x, y)}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to click mouse: {e}"}

def click_mouse(button: str = "left"):
    """Click mouse button with retry logic"""
    return execute_with_retry(_click_mouse_impl, button)

def drag_mouse(x: int, y: int, duration: float = 0.5):
    """Drag mouse to coordinates with validation"""
    try:
        # Validate coordinates
        valid, error_msg = _validate_coordinates(x, y)
        if not valid:
            return {"status": "error", "message": error_msg}
        
        # Get starting position
        start_x, start_y = pyautogui.position()
        
        # Perform drag
        pyautogui.dragTo(x, y, duration=max(duration, 0.8))  # Ensure minimum drag duration
        
        # Verify final position
        time.sleep(0.3)
        final_x, final_y = pyautogui.position()
        
        return {"status": "dragged", "from": (start_x, start_y), "to": (final_x, final_y), "duration": duration}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to drag mouse: {e}"}

def type_text(text: str):
    """Type text with error handling and confirmation"""
    try:
        if not text:
            return {"status": "error", "message": "No text provided to type"}
        
        pyautogui.write(text, interval=0.05)  # Faster typing
        time.sleep(0.2)  # Reduced delay
        
        return {"status": "typed", "text": text, "length": len(text)}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to type text: {e}"}

def press_key(key: str):
    """Press a single key with validation"""
    try:
        if not key:
            return {"status": "error", "message": "No key provided to press"}
        
        # Validate common keys (pyautogui will validate the rest)
        pyautogui.press(key)
        time.sleep(0.2)  # Reduced delay
        
        return {"status": "pressed", "key": key}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to press key '{key}': {e}"}

def hotkey(*keys: str):
    """Press a combination of keys with validation"""
    try:
        if not keys:
            return {"status": "error", "message": "No keys provided for hotkey"}
        
        pyautogui.hotkey(*keys)
        time.sleep(0.2)  # Reduced delay
        
        return {"status": "hotkey", "keys": list(keys), "combination": "+".join(keys)}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute hotkey {'+'.join(keys)}: {e}"}
