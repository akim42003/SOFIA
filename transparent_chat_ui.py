import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                            QTextEdit, QLineEdit, QPushButton, QToolBar,
                            QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QColor, QPalette
import tempfile
from datetime import datetime
import pyaudio
import wave
import whisper
import mss
import ollama

# Import existing SOFIA components
from gui_tools import take_screenshot
from chat_brain import ChatBrain, load_config
from OP_tool import process_image
from region_selector import RegionSelector


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


class AnalysisThread(QThread):
    response_received = pyqtSignal(str)

    def __init__(self, prompt, image_path=None):
        super().__init__()
        self.prompt = prompt
        self.image_path = image_path

    def run(self):
        try:
            messages = [{
                "role": "user",
                "content": self.prompt
            }]

            if self.image_path:
                messages[0]["images"] = [self.image_path]

            response = ""
            for chunk in ollama.chat(model="sofia2", messages=messages, stream=True):
                response += chunk['message']['content']

            self.response_received.emit(response)
        except Exception as e:
            self.response_received.emit(f"Error: {str(e)}")


class TransparentChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initSOFIA()
        self.audio_recorder = None
        self.whisper_model = None
        self.current_screenshot = None
        self.region_selector = None
        self.analysis_thread = None

    def initUI(self):
        # Window properties
        self.setWindowTitle('SOFIA Chat')
        self.setGeometry(100, 100, 400, 500)

        # Make window stay on top and semi-transparent
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.FramelessWindowHint |
                           Qt.WindowType.Tool)

        # Set transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.85)

        # Main container with background
        main_container = QWidget()
        main_container.setObjectName("mainContainer")
        main_container.setStyleSheet("""
            #mainContainer {
                background-color: rgba(30, 30, 30, 200);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 50);
            }
        """)

        # Main layout
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Title bar for dragging
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("""
            background-color: rgba(50, 50, 50, 180);
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
        """)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 0, 10, 0)

        # Title
        title_label = QPushButton("🤖 SOFIA Chat")
        title_label.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                font-weight: bold;
                text-align: left;
                padding-left: 5px;
                border: none;
            }
        """)
        title_label.setCursor(Qt.CursorShape.SizeAllCursor)

        # Window controls
        minimize_btn = QPushButton("_")
        close_btn = QPushButton("×")

        for btn in [minimize_btn, close_btn]:
            btn.setFixedSize(25, 25)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: white;
                    border: none;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 30);
                    border-radius: 3px;
                }
            """)

        minimize_btn.clicked.connect(self.showMinimized)
        close_btn.clicked.connect(self.hide)

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(minimize_btn)
        title_layout.addWidget(close_btn)
        title_bar.setLayout(title_layout)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(40, 40, 40, 150);
                color: white;
                border: none;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)

        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: rgba(40, 40, 40, 150);")
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(5, 5, 5, 5)

        # Tool buttons
        screenshot_btn = QPushButton("📸")
        region_btn = QPushButton("🔲")
        audio_btn = QPushButton("🎤")
        clear_btn = QPushButton("🗑️")

        for btn in [screenshot_btn, region_btn, audio_btn, clear_btn]:
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(70, 70, 70, 150);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 30);
                    border-radius: 5px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: rgba(90, 90, 90, 150);
                }
                QPushButton:pressed {
                    background-color: rgba(50, 50, 50, 150);
                }
            """)

        screenshot_btn.setToolTip("Take Screenshot (Ctrl+S)")
        region_btn.setToolTip("Select Region (Ctrl+R)")
        audio_btn.setToolTip("Record Audio (Ctrl+A)")
        clear_btn.setToolTip("Clear Chat")

        screenshot_btn.clicked.connect(self.take_screenshot)
        region_btn.clicked.connect(self.select_region)
        audio_btn.clicked.connect(self.toggle_audio_recording)
        clear_btn.clicked.connect(self.clear_chat)

        toolbar_layout.addWidget(screenshot_btn)
        toolbar_layout.addWidget(region_btn)
        toolbar_layout.addWidget(audio_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(clear_btn)
        toolbar.setLayout(toolbar_layout)

        # Input area
        input_container = QWidget()
        input_container.setStyleSheet("background-color: rgba(40, 40, 40, 150);")
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(5, 5, 5, 5)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask SOFIA anything...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(60, 60, 60, 150);
                color: white;
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: rgba(100, 150, 255, 150);
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)

        send_btn = QPushButton("→")
        send_btn.setFixedSize(35, 35)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 130, 180, 150);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(90, 150, 200, 150);
            }
        """)
        send_btn.clicked.connect(self.send_message)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)
        input_container.setLayout(input_layout)

        # Assemble main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        main_layout.addWidget(self.chat_display)
        main_layout.addWidget(toolbar)
        main_layout.addWidget(input_container)

        # Add to container
        container_layout.addWidget(title_bar)
        container_layout.addLayout(main_layout)
        main_container.setLayout(container_layout)

        # Set main widget layout
        window_layout = QVBoxLayout()
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(main_container)
        self.setLayout(window_layout)

        # System tray
        self.init_system_tray()

        # Enable dragging
        self.oldPos = None
        title_label.mousePressEvent = self.mousePressEvent
        title_label.mouseMoveEvent = self.mouseMoveEvent
        title_label.mouseReleaseEvent = self.mouseReleaseEvent

        # Keyboard shortcuts
        self.setup_shortcuts()

    def setup_shortcuts(self):
        # Import QShortcut here to avoid issues
        from PyQt6.QtGui import QShortcut

        screenshot_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        screenshot_shortcut.activated.connect(self.take_screenshot)

        region_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        region_shortcut.activated.connect(self.select_region)

        audio_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        audio_shortcut.activated.connect(self.toggle_audio_recording)

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
        try:
            messages, tools = load_config()
            self.config = {"messages": messages, "tools": tools}
            self.add_message("system", "SOFIA initialized and ready to help! 🤖")
        except Exception as e:
            self.add_message("system", f"Error initializing SOFIA: {e}")

    def add_message(self, sender, message):
        timestamp = datetime.now().strftime("%H:%M")

        if sender == "user":
            self.chat_display.append(f'<span style="color: #4a90e2;">[{timestamp}] You:</span> {message}')
        elif sender == "sofia":
            self.chat_display.append(f'<span style="color: #90ee90;">[{timestamp}] SOFIA:</span> {message}')
        elif sender == "system":
            self.chat_display.append(f'<span style="color: #ffa500;">[{timestamp}] System:</span> {message}')

        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def send_message(self):
        message = self.input_field.text().strip()
        if message:
            self.add_message("user", message)
            self.input_field.clear()

            # Process in thread
            self.analysis_thread = AnalysisThread(message, self.current_screenshot)
            self.analysis_thread.response_received.connect(lambda response: self.add_message("sofia", response))
            self.analysis_thread.start()

            # Clear screenshot after use
            self.current_screenshot = None

    def take_screenshot(self):
        self.setWindowOpacity(0.1)  # Almost invisible
        QTimer.singleShot(200, self._capture_screenshot)

    def _capture_screenshot(self):
        screenshot_result = take_screenshot()
        self.setWindowOpacity(0.85)  # Restore opacity

        if screenshot_result:
            self.current_screenshot = screenshot_result["path"]
            self.add_message("system", "📸 Screenshot captured! Ask me anything about it.")
            self.input_field.setFocus()

    def select_region(self):
        self.setWindowOpacity(0.1)
        self.region_selector = RegionSelector()
        self.region_selector.region_selected.connect(self.capture_region)
        self.region_selector.show()

    def capture_region(self, x, y, width, height):
        self.setWindowOpacity(0.85)

        if width > 0 and height > 0:
            with mss.mss() as sct:
                monitor = {"top": y, "left": x, "width": width, "height": height}
                screenshot = sct.grab(monitor)

                temp_path = os.path.join(tempfile.gettempdir(), f"region_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=temp_path)

                self.current_screenshot = temp_path
                self.add_message("system", "🔲 Region captured! Ask me anything about it.")
                self.input_field.setFocus()

    def toggle_audio_recording(self):
        if self.audio_recorder and self.audio_recorder.recording:
            self.audio_recorder.stop_recording()
            self.add_message("system", "🔴 Stopping audio recording...")
        else:
            self.audio_recorder = AudioRecorder()
            self.audio_recorder.finished.connect(self.process_audio)
            self.audio_recorder.start()
            self.add_message("system", "🎤 Recording audio... Press Ctrl+A to stop.")

    def process_audio(self, audio_path):
        self.add_message("system", "Processing audio...")

        if not self.whisper_model:
            self.whisper_model = whisper.load_model("base")

        result = self.whisper_model.transcribe(audio_path)
        text = result["text"]
        os.unlink(audio_path)

        if text.strip():
            self.add_message("system", f"📝 Transcription: {text}")

            # Analyze the transcription
            prompt = f"I just recorded this audio: '{text}'. Please summarize the key points and answer any questions mentioned."
            self.analysis_thread = AnalysisThread(prompt)
            self.analysis_thread.response_received.connect(lambda response: self.add_message("sofia2", response))
            self.analysis_thread.start()

    def clear_chat(self):
        self.chat_display.clear()
        self.add_message("system", "Chat cleared. Ready for new conversation!")

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    # Window dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.oldPos = None


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = TransparentChatWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
