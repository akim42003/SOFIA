import os
import tempfile
from datetime import datetime
import mss
import markdown
import html
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                            QTextEdit, QLineEdit, QPushButton, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence

from sofia.core.tools.desktop import take_screenshot
from sofia.core.brain_factory import get_brain_and_config
from sofia.core.brain import load_config
from sofia.ui.widgets.region_selector import RegionSelector
from sofia.ui.desktop.analysis_thread import AnalysisThread

# Memory management settings
MAX_SCREENSHOT_MESSAGES = 5  # Keep max 5 screenshot messages in memory
MAX_TOTAL_MESSAGES = 50      # Keep max 50 total messages in memory
from sofia.ui.desktop.system_tray import SystemTrayManager


class TransparentChatWindow(QWidget):
    """Main chat window for SOFIA desktop interface"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initSOFIA()
        self.current_screenshot = None
        self.region_selector = None
        self.analysis_thread = None
        self.chat_messages = []  # Store conversation history
        self.current_streaming_message = ""  # Track current streaming message
        self.is_streaming = False  # Track if we're currently streaming

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
        clear_btn = QPushButton("🗑️")

        for btn in [screenshot_btn, region_btn, clear_btn]:
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
        clear_btn.setToolTip("Clear Chat")

        screenshot_btn.clicked.connect(self.take_screenshot)
        region_btn.clicked.connect(self.select_region)
        clear_btn.clicked.connect(self.clear_chat)

        toolbar_layout.addWidget(screenshot_btn)
        toolbar_layout.addWidget(region_btn)
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

    def initSOFIA(self):
        """Initialize SOFIA components"""
        try:
            # Get brain instance and configuration using factory
            self.brain, messages, tools = get_brain_and_config()
            self.config = {"messages": messages, "tools": tools}
            
            # Initialize conversation with system messages
            self.chat_messages = messages.copy()
            
            # Display initial greeting message from assistant
            for msg in messages:
                if msg.get('role') == 'assistant':
                    self.add_message("sofia", msg.get('content', ''))
                    break
            
            # Determine which backend is being used
            from sofia.core.brain_factory import load_sofia_config
            config = load_sofia_config()
            backend = config.get('ai_backend', 'ollama')
            
            self.add_ui_status(f"SOFIA initialized with {backend.upper()} backend! 🤖")
        except Exception as e:
            self.add_ui_status(f"Error initializing SOFIA: {e}")
            self.brain = None

    def add_message(self, sender, message):
        """Add a message to the chat display"""
        timestamp = datetime.now().strftime("%H:%M")

        if sender == "user":
            # Escape user input for safety
            escaped_message = html.escape(message)
            self.chat_display.append(f'<span style="color: #4a90e2;">[{timestamp}] You:</span> {escaped_message}')
        elif sender == "sofia":
            # Parse markdown for SOFIA's responses
            parsed_message = self.parse_markdown(message)
            self.chat_display.append(f'<span style="color: #90ee90;">[{timestamp}] SOFIA:</span> {parsed_message}')
        elif sender == "system":
            # Escape system messages for safety
            escaped_message = html.escape(message)
            self.chat_display.append(f'<span style="color: #ffa500;">[{timestamp}] System:</span> {escaped_message}')

        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def cleanup_old_messages(self):
        """Clean up old messages to prevent memory accumulation"""
        # First, clean up excess screenshot messages
        screenshot_count = 0
        cleaned_messages = []
        
        # Process messages in reverse order to keep the most recent screenshots
        for msg in reversed(self.chat_messages):
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
        
        self.chat_messages = cleaned_messages

    def parse_markdown(self, text):
        """Convert markdown text to HTML for display"""
        try:
            # Configure markdown with useful extensions
            md = markdown.Markdown(extensions=[
                'markdown.extensions.fenced_code',
                'markdown.extensions.tables',
                'markdown.extensions.nl2br',
                'markdown.extensions.codehilite'
            ])
            
            # Convert markdown to HTML
            html_content = md.convert(text)
            
            # Escape any remaining unsafe content and return
            return html_content
        except Exception as e:
            # Fallback to escaped plain text if markdown parsing fails
            return html.escape(text)

    def add_ui_status(self, message):
        """Add a status message to UI display only (not to AI conversation)"""
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_display.append(f'<span style="color: #ffa500;">[{timestamp}] System:</span> {message}')
        
        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_last_message(self, new_content):
        """Update the last message in the chat display (for streaming)"""
        try:
            # Get the current cursor and document
            cursor = self.chat_display.textCursor()
            document = self.chat_display.document()
            
            # Move cursor to end of document
            cursor.movePosition(cursor.MoveOperation.End)
            
            # Find the last line that contains "SOFIA:"
            block = document.lastBlock()
            sofia_block = None
            
            while block.isValid():
                text = block.text()
                if "SOFIA:" in text:
                    sofia_block = block
                    break
                block = block.previous()
            
            if sofia_block:
                # Select the entire block
                cursor.setPosition(sofia_block.position())
                cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
                
                # Extract the timestamp and prefix
                original_text = sofia_block.text()
                import re
                match = re.match(r'(\[[^\]]+\] SOFIA:) .*', original_text)
                if match:
                    prefix = match.group(1)
                    # Use plain text during streaming (no markdown parsing)
                    escaped_content = html.escape(new_content)
                    cursor.insertHtml(f'<span style="color: #90ee90;">{prefix}</span> {escaped_content}')
                else:
                    # Fallback if pattern doesn't match
                    timestamp = datetime.now().strftime("%H:%M")
                    escaped_content = html.escape(new_content)
                    cursor.insertHtml(f'<span style="color: #90ee90;">[{timestamp}] SOFIA:</span> {escaped_content}')
                
                # Auto-scroll to bottom
                scrollbar = self.chat_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            else:
                # No SOFIA message found, add new one
                self.add_message("sofia", new_content)
                
        except Exception as e:
            # Fallback: just add a new message if updating fails
            print(f"Error updating message: {e}")
            # Don't add another message, just skip the update

    def send_message(self):
        """Send a message to SOFIA"""
        message = self.input_field.text().strip()
        if message:
            self.add_message("user", message)
            self.input_field.clear()

            # Add user message to conversation history
            user_message = {"role": "user", "content": message}
            if self.current_screenshot:
                user_message["images"] = [self.current_screenshot]
            self.chat_messages.append(user_message)

            # Clean up old messages before processing to manage memory
            self.cleanup_old_messages()

            # Process in thread with full context
            self.analysis_thread = AnalysisThread(
                message, 
                self.current_screenshot,
                brain=self.brain,
                chat_messages=self.chat_messages,
                tools=self.config.get('tools', [])
            )
            self.analysis_thread.streaming_chunk.connect(self.handle_streaming_chunk)
            self.analysis_thread.streaming_finished.connect(self.handle_streaming_finished)
            self.analysis_thread.response_received.connect(self.handle_response)
            self.analysis_thread.start()

            # Clear screenshot after use
            self.current_screenshot = None

    def handle_streaming_chunk(self, chunk):
        """Handle streaming chunk by accumulating it"""
        if not self.is_streaming:
            # First chunk - start streaming with plain text
            self.is_streaming = True
            self.current_streaming_message = chunk
            # Add first chunk as plain text (no markdown parsing)
            timestamp = datetime.now().strftime("%H:%M")
            escaped_content = html.escape(chunk)
            self.chat_display.append(f'<span style="color: #90ee90;">[{timestamp}] SOFIA:</span> {escaped_content}')
            
            # Auto-scroll to bottom
            scrollbar = self.chat_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        else:
            # Subsequent chunk - update the existing message
            self.current_streaming_message += chunk
            self.update_last_message(self.current_streaming_message)

    def handle_streaming_finished(self, full_response):
        """Handle when streaming is complete"""
        # Replace the plain text streaming message with markdown-formatted version
        try:
            # Get the current cursor and document
            cursor = self.chat_display.textCursor()
            document = self.chat_display.document()
            
            # Move cursor to end of document
            cursor.movePosition(cursor.MoveOperation.End)
            
            # Find the last line that contains "SOFIA:"
            block = document.lastBlock()
            sofia_block = None
            
            while block.isValid():
                text = block.text()
                if "SOFIA:" in text:
                    sofia_block = block
                    break
                block = block.previous()
            
            if sofia_block:
                # Select the entire block
                cursor.setPosition(sofia_block.position())
                cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
                
                # Extract the timestamp and prefix
                original_text = sofia_block.text()
                import re
                match = re.match(r'(\[[^\]]+\] SOFIA:) .*', original_text)
                if match:
                    prefix = match.group(1)
                    # Now apply markdown parsing to the final response
                    parsed_content = self.parse_markdown(full_response)
                    cursor.insertHtml(f'<span style="color: #90ee90;">{prefix}</span> {parsed_content}')
                
                # Auto-scroll to bottom
                scrollbar = self.chat_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
        except Exception as e:
            print(f"Error applying final markdown formatting: {e}")
        
        # Update conversation history
        if self.chat_messages:
            # Add the assistant's response to history
            self.chat_messages.append({
                "role": "assistant", 
                "content": full_response
            })
        
        # Reset streaming state
        self.current_streaming_message = ""
        self.is_streaming = False

    def handle_response(self, response):
        """Handle non-streaming response (fallback for errors)"""
        self.add_message("sofia", response)
        
        # Add to conversation history
        if self.chat_messages:
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
            self.add_ui_status("📸 Screenshot captured! Ask me anything about it.")
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
                self.add_ui_status("🔲 Region captured! Ask me anything about it.")
                self.input_field.setFocus()


    def clear_chat(self):
        """Clear the chat history"""
        self.chat_display.clear()
        # Reset conversation history to initial system messages
        try:
            messages, tools = load_config()
            self.chat_messages = messages.copy()
        except Exception as e:
            self.chat_messages = []
        self.add_ui_status("Chat cleared. Ready for new conversation!")

    def toggle_visibility(self):
        """Toggle window visibility"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
    
    def closeEvent(self, event):
        """Handle window close event to ensure proper cleanup"""
        # Stop any running threads
        
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