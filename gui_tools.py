import pyautogui
import tempfile
import mss
from PIL import Image

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
    pyautogui.moveTo(x, y)
    return {"status": "moved"}

def click_mouse(button: str = "left"):
    pyautogui.click(button=button)
    return {"status": "clicked"}

def drag_mouse(x: int, y: int, duration: float = 0.5):
    pyautogui.dragTo(x, y, duration=duration)
    return {"status": "dragged"}

def type_text(text: str):
    pyautogui.write(text)
    return {"status": "typed"}

def press_key(key: str):
    pyautogui.press(key)
    return {"status": f"pressed {key}"}

def hotkey(*keys: str):
    pyautogui.hotkey(*keys)
    return {"status": f"hotkey {'+'.join(keys)}"}
