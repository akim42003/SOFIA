import os
import tempfile
from datetime import datetime
import whisper
import mss
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                            QTextEdit, QLineEdit, QPushButton, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence

from sofia.core.tools.desktop import take_screenshot
from sofia.core.brain import ChatBrain, load_config
from sofia.ui.widgets.region_selector import RegionSelector
from sofia.ui.desktop.audio_recorder import AudioRecorder
from sofia.ui.desktop.analysis_thread import AnalysisThread
from sofia.ui.desktop.system_tray import SystemTrayManager


class TransparentChatWindow(QWidget):
    """Main chat window for SOFIA desktop interface"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initSOFIA()
        self.audio_recorder = None
        self.whisper_model = None
        self.current_screenshot = None
        self.region_selector = None
        self.analysis_thread = None
        self.chat_messages = []  # Store conversation history

    def initUI(self):
        """Initialize the user interface"""
        # Window properties
        self.setWindowTitle('SOFIA Chat')
        self.setGeometry(100, 100, 400, 500)

        # Make window stay on top and resizable
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Window)
        
        # Enable resizing
        self.setMinimumSize(300, 350)
        self.setMaximumSize(800, 1000)

        # Set window opacity
        self.setWindowOpacity(0.95)

        # Set window background
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 240);
                color: white;
            }
        """)

        self._setup_chat_display()
        self._setup_toolbar()
        self._setup_input_area()
        self._setup_layout()
        
        # System tray
        self.system_tray = SystemTrayManager(self)

        # Keyboard shortcuts
        self.setup_shortcuts()

    def _setup_chat_display(self):
        """Setup the chat display area"""
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(40, 40, 40, 200);
                color: white;
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 5px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)

    def _setup_toolbar(self):
        """Setup the toolbar with action buttons"""
        self.toolbar = QWidget()
        self.toolbar.setStyleSheet("""
            background-color: rgba(40, 40, 40, 200);
            border-radius: 5px;
            border: 1px solid rgba(255, 255, 255, 30);
        """)
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
        self.toolbar.setLayout(toolbar_layout)

    def _setup_input_area(self):
        """Setup the input area for typing messages"""
        input_container = QWidget()
        input_container.setStyleSheet("""
            background-color: rgba(40, 40, 40, 200);
            border-radius: 5px;
            border: 1px solid rgba(255, 255, 255, 30);
        """)
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
        
        self.input_container = input_container

    def _setup_layout(self):
        """Setup the main layout"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        main_layout.addWidget(self.chat_display)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.input_container)
        
        self.setLayout(main_layout)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        screenshot_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        screenshot_shortcut.activated.connect(self.take_screenshot)

        region_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        region_shortcut.activated.connect(self.select_region)

        audio_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        audio_shortcut.activated.connect(self.toggle_audio_recording)

    def initSOFIA(self):
        """Initialize SOFIA components"""
        try:
            messages, tools = load_config()
            self.config = {"messages": messages, "tools": tools}
            
            # Initialize ChatBrain for tool execution
            import ollama
            self.brain = ChatBrain(ollama.chat)
            
            # Initialize conversation with system messages
            self.chat_messages = messages.copy()
            
            self.add_message("system", "SOFIA initialized with full tool support! 🤖")
        except Exception as e:
            self.add_message("system", f"Error initializing SOFIA: {e}")
            self.brain = None

    def add_message(self, sender, message):
        """Add a message to the chat display"""
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
        """Send a message to SOFIA"""
        message = self.input_field.text().strip()
        if message:
            self.add_message("user", message)
            self.input_field.clear()

            # Process in thread with full context
            self.analysis_thread = AnalysisThread(
                message, 
                self.current_screenshot,
                brain=self.brain,
                chat_messages=self.chat_messages,
                tools=self.config.get('tools', [])
            )
            self.analysis_thread.response_received.connect(self.handle_response)
            self.analysis_thread.start()

            # Clear screenshot after use
            self.current_screenshot = None

    def handle_response(self, response):
        """Handle response and update conversation history"""
        self.add_message("sofia", response)
        
        # Update conversation history
        if self.chat_messages:
            # Add the assistant's response to history
            self.chat_messages.append({
                "role": "assistant", 
                "content": response
            })

    def take_screenshot(self):
        """Take a screenshot"""
        self.setWindowOpacity(0.1)  # Almost invisible
        QTimer.singleShot(200, self._capture_screenshot)

    def _capture_screenshot(self):
        """Capture the screenshot"""
        screenshot_result = take_screenshot()
        self.setWindowOpacity(0.95)  # Restore opacity

        if screenshot_result:
            self.current_screenshot = screenshot_result["path"]
            self.add_message("system", "📸 Screenshot captured! Ask me anything about it.")
            self.input_field.setFocus()

    def select_region(self):
        """Select a region for screenshot"""
        self.setWindowOpacity(0.1)
        self.region_selector = RegionSelector()
        self.region_selector.region_selected.connect(self.capture_region)
        self.region_selector.show()

    def capture_region(self, x, y, width, height):
        """Capture a selected region"""
        self.setWindowOpacity(0.95)

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
        """Toggle audio recording"""
        if self.audio_recorder and self.audio_recorder.recording:
            self.audio_recorder.stop_recording()
            self.add_message("system", "🔴 Stopping audio recording...")
        else:
            self.audio_recorder = AudioRecorder()
            self.audio_recorder.finished.connect(self.process_audio)
            self.audio_recorder.start()
            self.add_message("system", "🎤 Recording audio... Press Ctrl+A to stop.")

    def process_audio(self, audio_path):
        """Process recorded audio"""
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
            self.analysis_thread = AnalysisThread(
                prompt,
                brain=self.brain,
                chat_messages=self.chat_messages,
                tools=self.config.get('tools', [])
            )
            self.analysis_thread.response_received.connect(self.handle_response)
            self.analysis_thread.start()

    def clear_chat(self):
        """Clear the chat history"""
        self.chat_display.clear()
        # Reset conversation history to initial system messages
        try:
            messages, tools = load_config()
            self.chat_messages = messages.copy()
        except Exception as e:
            self.chat_messages = []
        self.add_message("system", "Chat cleared. Ready for new conversation!")

    def toggle_visibility(self):
        """Toggle window visibility"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
    
    def closeEvent(self, event):
        """Handle window close event to ensure proper cleanup"""
        # Stop any running threads
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            if self.audio_recorder.recording:
                self.audio_recorder.stop_recording()
            if self.audio_recorder.isRunning():
                self.audio_recorder.wait()
        
        if hasattr(self, 'analysis_thread') and self.analysis_thread:
            if self.analysis_thread.isRunning():
                self.analysis_thread.wait()
        
        # Clean up system tray
        if hasattr(self, 'system_tray'):
            self.system_tray.hide()
        
        # Accept the close event
        event.accept()
        
        # Force application quit
        QApplication.quit()