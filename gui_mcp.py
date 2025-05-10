#use pyautogui to give mouse and keyboard control
import pyautogui

screen_x, screen_y = pyautogui.size()
abs_pos = pyautogui.position()
std_pos = [abs_pos[0], screen_y - abs_pos[1]]

print(std_pos)
