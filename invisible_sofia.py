import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout,
                            QMenu, QSystemTrayIcon, QLabel, QHBoxLayout, QTextEdit)
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QPainter, QColor, QCursor, QAction, QPixmap, QKeySequence, QShortcut
import pyaudio
import wave
import tempfile
from datetime import datetime
from pathlib import Path

# Import existing SOFIA components
from gui_tools import take_screenshot
from chat_brain import ChatBrain, load_config
from OP_tool import process_image
from region_selector import RegionSelector
from chat_dialog import ChatDialog
import whisper
import mss
import ollama


class ResponsePopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('SOFIA Response')
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Tool)
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        # Response text area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)

        # Close button
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
        """)

        layout.addWidget(self.text_area)
        layout.addWidget(close_btn)
        self.setLayout(layout)

    def show_response(self, text):
        self.text_area.setText(text)
        self.show()
        # Position near the floating widget
        if self.parent():
            parent_pos = self.parent().pos()
            self.move(parent_pos.x() + 70, parent_pos.y())


class AudioRecorder(QThread):
    finished = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recording = False
        self.frames = []

    def run(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)

        self.recording = True
        self.frames = []

        while self.recording:
            data = stream.read(CHUNK)
            self.frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save audio to temp file
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        wf = wave.open(temp_audio.name, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()

        self.finished.emit(temp_audio.name)

    def stop_recording(self):
        self.recording = False


class FloatingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initSOFIA()
        self.oldPos = None
        self.audio_recorder = None
        self.whisper_model = None
        self.response_popup = ResponsePopup(self)
        self.region_selector = None

    def initUI(self):
        # Window setup
        self.setWindowTitle('SOFIA Assistant')
        self.setFixedSize(60, 60)

        # Make window stay on top and frameless
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Tool)

        # Semi-transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Create circular button
        self.main_btn = QPushButton('🤖', self)
        self.main_btn.setFixedSize(50, 50)
        self.main_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(50, 50, 200, 180);
                color: white;
                border-radius: 25px;
                font-size: 24px;
                border: 2px solid rgba(255, 255, 255, 100);
            }
            QPushButton:hover {
                background-color: rgba(70, 70, 220, 200);
            }
            QPushButton:pressed {
                background-color: rgba(30, 30, 180, 200);
            }
        """)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.main_btn)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        # Context menu
        self.main_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.main_btn.customContextMenuRequested.connect(self.show_context_menu)

        # Click action
        self.main_btn.clicked.connect(self.quick_screenshot)

        # System tray
        self.init_system_tray()

        # Position window
        self.move(100, 100)

        # Setup keyboard shortcuts
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Setup global keyboard shortcuts"""
        # Screenshot shortcut
        screenshot_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        screenshot_shortcut.activated.connect(self.quick_screenshot)

        # Region selection shortcut
        region_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        region_shortcut.activated.connect(self.analyze_region)

        # Audio recording shortcut
        audio_shortcut = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        audio_shortcut.activated.connect(self.toggle_audio_recording)

        # Hide/Show shortcut
        visibility_shortcut = QShortcut(QKeySequence("Ctrl+Shift+H"), self)
        visibility_shortcut.activated.connect(self.toggle_visibility)

    def init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme('applications-system'))

        tray_menu = QMenu()

        show_action = QAction("Show/Hide", self)
        show_action.triggered.connect(self.toggle_visibility)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.quit)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def initSOFIA(self):
        # Load SOFIA configuration
        try:
            messages, tools = load_config()
            self.config = {"messages": messages, "tools": tools}
            self.chat_brain = True  # We'll use ollama.chat directly
        except Exception as e:
            print(f"Error initializing SOFIA: {e}")
            self.config = None
            self.chat_brain = None

    def show_context_menu(self, position):
        menu = QMenu(self)

        # Screenshot actions
        screenshot_action = QAction("📸 Analyze Screenshot", self)
        screenshot_action.triggered.connect(self.analyze_screenshot)

        region_action = QAction("🔲 Analyze Region", self)
        region_action.triggered.connect(self.analyze_region)

        # Audio actions
        audio_action = QAction("🎤 Record Audio", self)
        audio_action.triggered.connect(self.toggle_audio_recording)

        # Other actions
        hide_action = QAction("👻 Hide", self)
        hide_action.triggered.connect(self.hide)

        exit_action = QAction("❌ Exit", self)
        exit_action.triggered.connect(QApplication.quit)

        menu.addAction(screenshot_action)
        menu.addAction(region_action)
        menu.addSeparator()
        menu.addAction(audio_action)
        menu.addSeparator()
        menu.addAction(hide_action)
        menu.addAction(exit_action)

        menu.exec(self.mapToGlobal(position))

    def quick_screenshot(self):
        """Quick screenshot and analysis"""
        self.hide()  # Hide widget during screenshot
        QTimer.singleShot(200, self._capture_and_show_dialog)

    def _capture_and_show_dialog(self):
        # Take screenshot first
        screenshot_result = take_screenshot()
        self.show()

        if screenshot_result and self.chat_brain:
            self.current_screenshot = screenshot_result["path"]

            # Show dialog to get user input
            dialog = ChatDialog(self, "What would you like to know about this screenshot?")
            dialog.message_submitted.connect(self._analyze_with_prompt)
            dialog.exec()

    def _analyze_with_prompt(self, user_prompt):
        """Analyze screenshot with user's specific prompt"""
        if hasattr(self, 'current_screenshot') and self.current_screenshot:
            # Process with OmniParser
            result = process_image(self.current_screenshot)

            # Use user's prompt
            messages = [
                {
                    "role": "user",
                    "content": user_prompt,
                    "images": [self.current_screenshot]
                }
            ]

            response = ""
            for chunk in ollama.chat(model="sofia2", messages=messages, stream=True):
                response += chunk['message']['content']

            # Show response in popup
            self.response_popup.show_response(response)

            # Clean up
            import os
            if os.path.exists(self.current_screenshot):
                os.unlink(self.current_screenshot)
            self.current_screenshot = None

    def _capture_and_analyze(self):
        # Take screenshot
        screenshot_result = take_screenshot()
        self.show()

        if screenshot_result and self.chat_brain:
            screenshot_path = screenshot_result["path"]
            # Process with OmniParser
            result = process_image(screenshot_path)

            # Create analysis prompt
            prompt = "What's on the screen? Describe what you see and any important information."

            # Get response from SOFIA using ollama directly for streaming
            messages = [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [screenshot_path]
                }
            ]

            response = ""
            for chunk in ollama.chat(model="sofia2", messages=messages, stream=True):
                response += chunk['message']['content']

            # Show response in popup
            self.response_popup.show_response(response)

    def analyze_screenshot(self):
        """Full screenshot analysis"""
        self.quick_screenshot()

    def analyze_region(self):
        """Region selection for analysis"""
        self.hide()
        self.region_selector = RegionSelector()
        self.region_selector.region_selected.connect(self.capture_region)
        self.region_selector.show()

    def capture_region(self, x, y, width, height):
        """Capture and analyze selected region"""
        self.show()

        if width > 0 and height > 0:
            # Capture the selected region
            with mss.mss() as sct:
                monitor = {"top": y, "left": x, "width": width, "height": height}
                screenshot = sct.grab(monitor)

                # Save to temp file
                temp_path = os.path.join(tempfile.gettempdir(), f"region_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=temp_path)

                if self.chat_brain:
                    self.current_screenshot = temp_path

                    # Show dialog to get user input
                    dialog = ChatDialog(self, "What would you like to know about this selected region?")
                    dialog.message_submitted.connect(self._analyze_with_prompt)
                    dialog.exec()

    def toggle_audio_recording(self):
        """Start/stop audio recording"""
        if self.audio_recorder and self.audio_recorder.recording:
            # Stop recording
            self.audio_recorder.stop_recording()
            self.main_btn.setText('🤖')
        else:
            # Start recording
            self.audio_recorder = AudioRecorder()
            self.audio_recorder.finished.connect(self.process_audio)
            self.audio_recorder.start()
            self.main_btn.setText('🔴')

    def process_audio(self, audio_path):
        """Process recorded audio with Whisper"""
        if not self.whisper_model:
            self.whisper_model = whisper.load_model("base")

        # Transcribe
        result = self.whisper_model.transcribe(audio_path)
        text = result["text"]

        # Clean up temp file
        os.unlink(audio_path)

        if text.strip():
            # Send to SOFIA for analysis
            prompt = f"I just recorded this audio: '{text}'. Please summarize the key points and answer any questions mentioned."

            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = ""
            for chunk in ollama.chat(model="sofia", messages=messages, stream=True):
                response += chunk['message']['content']

            # Show full response with transcription
            full_response = f"📝 Transcription:\n{text}\n\n🤖 SOFIA's Analysis:\n{response}"
            self.response_popup.show_response(full_response)

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    # Mouse events for dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.oldPos = None


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray

    widget = FloatingWidget()
    widget.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
