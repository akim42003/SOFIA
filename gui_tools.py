import pyautogui
import tempfile

def take_screenshot():
    screenshot = pyautogui.screenshot()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    path = tmp.name
    tmp.close()
    screenshot.save(path)
    return {"path": path}

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
