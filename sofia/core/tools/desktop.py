import pyautogui
import tempfile
import mss
import time
import os
from PIL import Image

# Configure pyautogui for reliability
pyautogui.FAILSAFE = False  # Disable failsafe for automated use
pyautogui.PAUSE = 0.5       # Increased pause between actions for better stability

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
    """
    with mss.mss() as sct:
        # monitors[0] = virtual desktop, monitors[1] = primary display
        mon = sct.monitors[1]                # {'left':0,'top':0,'width':..., 'height':...}
        raw = sct.grab(mon)                  # raw BGRA bytes

    img = Image.frombytes("RGB", raw.size, raw.rgb)

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    tmp.close()                              # keep the file on disk

    return {"path": tmp.name}

def move_mouse(x: int, y: int):
    """Move mouse to specific coordinates with validation and error handling"""
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
        time.sleep(0.3)  # Increased delay to ensure position is updated
        new_x, new_y = pyautogui.position()
        
        if abs(new_x - x) <= 2 and abs(new_y - y) <= 2:  # Allow small tolerance
            return {"status": "moved", "from": (current_x, current_y), "to": (new_x, new_y)}
        else:
            return {"status": "error", "message": f"Mouse moved to ({new_x}, {new_y}) instead of ({x}, {y})"}
            
    except Exception as e:
        return {"status": "error", "message": f"Failed to move mouse: {e}"}

def click_mouse(button: str = "left"):
    """Click mouse button with validation and confirmation"""
    try:
        # Validate button type
        valid_buttons = ["left", "right", "middle"]
        if button not in valid_buttons:
            return {"status": "error", "message": f"Invalid button '{button}'. Must be one of: {valid_buttons}"}
        
        # Get current position
        x, y = pyautogui.position()
        
        # Perform click
        pyautogui.click(button=button)
        
        # Longer delay to allow UI to respond
        time.sleep(0.5)
        
        return {"status": "clicked", "button": button, "position": (x, y)}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to click mouse: {e}"}

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
        
        pyautogui.write(text, interval=0.1)  # Increased interval between keystrokes for reliability
        time.sleep(0.3)  # Allow UI to process
        
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
        time.sleep(0.3)  # Allow UI to process
        
        return {"status": "pressed", "key": key}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to press key '{key}': {e}"}

def hotkey(*keys: str):
    """Press a combination of keys with validation"""
    try:
        if not keys:
            return {"status": "error", "message": "No keys provided for hotkey"}
        
        pyautogui.hotkey(*keys)
        time.sleep(0.3)  # Allow UI to process
        
        return {"status": "hotkey", "keys": list(keys), "combination": "+".join(keys)}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute hotkey {'+'.join(keys)}: {e}"}
