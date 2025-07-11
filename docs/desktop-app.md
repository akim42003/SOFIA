# Desktop Application

The SOFIA Desktop Application provides a native GUI interface built with PyQt6, offering real-time AI interaction, drag-and-drop image support, and system integration capabilities.

## Overview

The desktop application (`sofia/ui/desktop/`) delivers a rich, responsive user experience with advanced features like streaming responses, background processing, and seamless tool execution visualization.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Desktop Application                           │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer                                              │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Main Window    │  │  System Tray    │                     │
│  │  (PyQt6)        │  │  Integration    │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Chat Interface                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Message        │  │  Input Field    │  │  Image Upload   │ │
│  │  Display        │  │  & Controls     │  │  (Drag & Drop)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Background Processing                                          │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  Analysis       │  │  Streaming      │                     │
│  │  Thread         │  │  Responses      │                     │
│  └─────────────────┘  └─────────────────┘                     │
├─────────────────────────────────────────────────────────────────┤
│  Brain Integration                                              │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  OpenAI Brain   │  │  Ollama Brain   │                     │
│  │  Support        │  │  Support        │                     │
│  └─────────────────┘  └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### Main Application (`main.py`)

The entry point manages application lifecycle and system integration:

```python
class SofiaApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        
        # Set application properties
        self.setApplicationName(\"SOFIA\")
        self.setApplicationVersion(\"2.0.0\")
        self.setOrganizationName(\"SOFIA Team\")
        
        # Initialize brain and configuration
        self.brain, self.messages, self.tools = get_brain_and_config()
        
        # Create main window
        self.chat_window = ChatWindow(
            brain=self.brain,
            messages=self.messages,
            tools=self.tools
        )
        
        # System tray integration
        self.setup_system_tray()
        
        # Show main window
        self.chat_window.show()
    
    def setup_system_tray(self):
        \"\"\"Setup system tray icon and menu\"\"\"
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon(\"assets/sofia_icon.png\"))
            
            # Create tray menu
            tray_menu = QMenu()
            
            show_action = QAction(\"Show SOFIA\", self)
            show_action.triggered.connect(self.chat_window.show)
            tray_menu.addAction(show_action)
            
            quit_action = QAction(\"Quit\", self)
            quit_action.triggered.connect(self.quit)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
```

### Chat Window (`chat_window.py`)

The main interface component handling user interaction:

```python
class ChatWindow(QMainWindow):
    def __init__(self, brain, messages, tools):
        super().__init__()
        
        self.brain = brain
        self.messages = messages.copy()
        self.tools = tools
        
        # Streaming state management
        self.is_streaming = False
        self.current_streaming_message = \"\"
        
        self.setup_ui()
        self.setup_drag_drop()
        
    def setup_ui(self):
        \"\"\"Initialize the user interface\"\"\"
        self.setWindowTitle(\"SOFIA - AI Assistant\")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(\"\"\"
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
            }
        \"\"\")
        layout.addWidget(self.chat_display)
        
        # Input area
        self.setup_input_area(layout)
        
        # Load initial messages
        self.load_initial_messages()
    
    def setup_input_area(self, layout):
        \"\"\"Setup input field and controls\"\"\"
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        
        # Text input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(\"Type your message here...\")
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.setStyleSheet(\"\"\"
            QLineEdit {
                padding: 12px;
                border: 2px solid #007bff;
                border-radius: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0056b3;
            }
        \"\"\")
        input_layout.addWidget(self.input_field)
        
        # Send button
        self.send_button = QPushButton(\"Send\")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet(\"\"\"
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        \"\"\")
        input_layout.addWidget(self.send_button)
        
        layout.addWidget(input_widget)
```

### Drag and Drop Support

Advanced image handling with drag-and-drop functionality:

```python
def setup_drag_drop(self):
    \"\"\"Enable drag and drop for images\"\"\"
    self.setAcceptDrops(True)
    
    # Visual feedback for drag operations
    self.drag_overlay = QLabel(self)
    self.drag_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.drag_overlay.setText(\"Drop images here\")
    self.drag_overlay.setStyleSheet(\"\"\"
        QLabel {
            background-color: rgba(0, 123, 255, 0.1);
            border: 2px dashed #007bff;
            border-radius: 12px;
            font-size: 18px;
            color: #007bff;
            font-weight: bold;
        }
    \"\"\")
    self.drag_overlay.hide()

def dragEnterEvent(self, event):
    \"\"\"Handle drag enter event\"\"\"
    if event.mimeData().hasUrls():
        # Check if any URL is an image file
        for url in event.mimeData().urls():
            if self.is_image_file(url.toLocalFile()):
                event.acceptProposedAction()
                self.show_drag_overlay()
                return
    event.ignore()

def dragLeaveEvent(self, event):
    \"\"\"Handle drag leave event\"\"\"
    self.hide_drag_overlay()

def dropEvent(self, event):
    \"\"\"Handle file drop event\"\"\"
    self.hide_drag_overlay()
    
    image_files = []
    for url in event.mimeData().urls():
        file_path = url.toLocalFile()
        if self.is_image_file(file_path):
            image_files.append(file_path)
    
    if image_files:
        self.handle_image_upload(image_files)
        event.acceptProposedAction()
    else:
        QMessageBox.warning(self, \"Invalid Files\", 
                          \"Please drop only image files (PNG, JPG, JPEG, WebP)\")

def is_image_file(self, file_path: str) -> bool:
    \"\"\"Check if file is a supported image format\"\"\"
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
    return Path(file_path).suffix.lower() in supported_formats

def handle_image_upload(self, image_files: List[str]):
    \"\"\"Process uploaded images\"\"\"
    for image_path in image_files:
        # Add image to current message context
        self.current_images = getattr(self, 'current_images', [])
        self.current_images.append(image_path)
        
        # Show image preview in chat
        self.add_image_preview(image_path)
    
    # Update input placeholder
    if hasattr(self, 'current_images') and self.current_images:
        self.input_field.setPlaceholderText(
            f\"Type message about {len(self.current_images)} image(s)...\"
        )
```

### Analysis Thread (`analysis_thread.py`)

Background processing for AI responses without blocking the UI:

```python
class AnalysisThread(QThread):
    \"\"\"Thread for AI analysis and tool execution\"\"\"
    response_received = pyqtSignal(str)
    streaming_chunk = pyqtSignal(str)
    streaming_finished = pyqtSignal(str)
    
    def __init__(self, prompt, image_path=None, brain=None, chat_messages=None, tools=None):
        super().__init__()
        self.prompt = prompt
        self.image_path = image_path
        self.brain = brain
        self.chat_messages = chat_messages or []
        self.tools = tools or []
    
    def run(self):
        \"\"\"Execute AI processing in background thread\"\"\"
        try:
            # Build message with proper context
            user_message = {
                \"role\": \"user\",
                \"content\": self.prompt
            }
            
            if self.image_path:
                user_message[\"images\"] = [self.image_path]
            
            # Add to conversation history
            messages = self.chat_messages.copy()
            messages.append(user_message)
            
            # Process based on brain type
            if isinstance(self.brain, OpenAIChatBrain):
                self.process_openai_response(messages)
            else:
                self.process_ollama_response(messages)
                
        except Exception as e:
            self.response_received.emit(f\"Error: {str(e)}\")
    
    def process_openai_response(self, messages):
        \"\"\"Handle OpenAI streaming response\"\"\"
        from sofia.core.openai_brain import convert_messages_to_openai_format, convert_tools_to_openai_format
        
        openai_messages = convert_messages_to_openai_format(messages)
        openai_tools = convert_tools_to_openai_format(self.tools)
        
        # Make streaming API call
        response = self.brain.client.chat.completions.create(
            model=self.brain.model,
            messages=openai_messages,
            tools=openai_tools if openai_tools else None,
            stream=True
        )
        
        full_content = \"\"
        tool_calls = []
        
        # Process streaming chunks
        for chunk in response:
            delta = chunk.choices[0].delta
            
            if delta.content:
                full_content += delta.content
                self.streaming_chunk.emit(delta.content)
            
            # Accumulate tool calls
            if delta.tool_calls:
                self.accumulate_tool_calls(delta.tool_calls, tool_calls)
        
        # Execute tools if present
        if tool_calls:
            self.execute_openai_tools(tool_calls, messages, full_content)
        else:
            self.streaming_finished.emit(full_content)
    
    def process_ollama_response(self, messages):
        \"\"\"Handle Ollama streaming response\"\"\"
        import ollama
        
        response = \"\"
        for chunk in ollama.chat(
            model=\"sofia2\", 
            messages=messages, 
            tools=self.tools, 
            stream=True
        ):
            # Handle tool calls
            if chunk['message'].get('tool_calls'):
                self.brain.execute_tool_calls(chunk, messages)
            
            # Process content
            content = chunk['message'].get('content', '')
            if content:
                response += content
                self.streaming_chunk.emit(content)
        
        self.streaming_finished.emit(response)
```

### Streaming Response Handling

Real-time response display with proper message management:

```python
def handle_streaming_chunk(self, chunk: str):
    \"\"\"Process individual streaming chunks\"\"\"
    if not self.is_streaming:
        # Start new streaming message
        self.is_streaming = True
        self.current_streaming_message = chunk
        self.add_message(\"sofia\", chunk)
    else:
        # Append to existing streaming message
        self.current_streaming_message += chunk
        self.update_last_message(self.current_streaming_message)

def handle_streaming_finished(self, complete_response: str):
    \"\"\"Handle completion of streaming response\"\"\"
    self.is_streaming = False
    self.current_streaming_message = \"\"
    
    # Update message history
    self.messages.append({
        \"role\": \"assistant\", 
        \"content\": complete_response
    })
    
    # Re-enable input
    self.input_field.setEnabled(True)
    self.send_button.setEnabled(True)
    self.input_field.setFocus()

def update_last_message(self, content: str):
    \"\"\"Update the last message in the chat display\"\"\"
    # Get current HTML content
    html = self.chat_display.toHtml()
    
    # Find last SOFIA message and update it
    # This is a simplified version - actual implementation
    # would use proper HTML parsing and manipulation
    lines = html.split('\\n')
    for i in range(len(lines) - 1, -1, -1):
        if 'sofia-message' in lines[i]:
            # Update the message content
            lines[i] = self.format_message_html(\"sofia\", content)
            break
    
    # Update display
    updated_html = '\\n'.join(lines)
    self.chat_display.setHtml(updated_html)
    
    # Scroll to bottom
    self.chat_display.verticalScrollBar().setValue(
        self.chat_display.verticalScrollBar().maximum()
    )
```

### Message Display and Formatting

Rich text formatting for enhanced user experience:

```python
def add_message(self, sender: str, message: str, images: List[str] = None):
    \"\"\"Add a message to the chat display\"\"\"
    # Format timestamp
    timestamp = datetime.now().strftime(\"%H:%M\")
    
    # Create message HTML
    message_html = self.format_message_html(sender, message, timestamp, images)
    
    # Append to chat display
    cursor = self.chat_display.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertHtml(message_html)
    
    # Auto-scroll to bottom
    self.chat_display.verticalScrollBar().setValue(
        self.chat_display.verticalScrollBar().maximum()
    )

def format_message_html(self, sender: str, message: str, timestamp: str = None, images: List[str] = None) -> str:
    \"\"\"Format message as HTML with styling\"\"\"
    
    # Determine message styling
    if sender == \"sofia\":
        bubble_class = \"sofia-message\"
        sender_color = \"#007bff\"
        bubble_color = \"#e3f2fd\"
    else:
        bubble_class = \"user-message\"
        sender_color = \"#28a745\"
        bubble_color = \"#e8f5e9\"
    
    # Build HTML
    html = f\"\"\"
    <div class=\"{bubble_class}\" style=\"
        margin: 10px 0;
        padding: 12px;
        background-color: {bubble_color};
        border-radius: 12px;
        border-left: 4px solid {sender_color};
    \">
        <div style=\"
            font-weight: bold;
            color: {sender_color};
            margin-bottom: 6px;
            font-size: 13px;
        \">
            {sender.title()} {f'• {timestamp}' if timestamp else ''}
        </div>
        <div style=\"
            color: #333;
            line-height: 1.4;
            white-space: pre-wrap;
        \">
            {self.format_message_content(message)}
        </div>
    \"\"\"
    
    # Add images if present
    if images:
        html += self.format_images_html(images)
    
    html += \"</div>\"
    
    return html

def format_message_content(self, content: str) -> str:
    \"\"\"Format message content with markdown-like styling\"\"\"
    import re
    
    # Convert basic markdown to HTML
    content = re.sub(r'\\*\\*(.*?)\\*\\*', r'<strong>\\1</strong>', content)  # Bold
    content = re.sub(r'\\*(.*?)\\*', r'<em>\\1</em>', content)  # Italic
    content = re.sub(r'`(.*?)`', r'<code style=\"background-color: #f1f3f4; padding: 2px 4px; border-radius: 3px;\">\\1</code>', content)  # Code
    
    # Convert URLs to links
    url_pattern = r'(https?://[^\\s]+)'
    content = re.sub(url_pattern, r'<a href=\"\\1\" style=\"color: #007bff;\">\\1</a>', content)
    
    return content

def format_images_html(self, images: List[str]) -> str:
    \"\"\"Format images for display in chat\"\"\"
    html = \"<div style='margin-top: 10px;'>\"
    
    for image_path in images:
        if os.path.exists(image_path):
            # Create thumbnail
            thumbnail_path = self.create_thumbnail(image_path)
            html += f\"\"\"
            <img src=\"file://{thumbnail_path}\" 
                 style=\"
                     max-width: 300px;
                     max-height: 200px;
                     margin: 5px;
                     border-radius: 8px;
                     cursor: pointer;
                 \"
                 onclick=\"window.open('file://{image_path}')\"
                 title=\"Click to view full size\"
            />
            \"\"\"
    
    html += \"</div>\"
    return html
```

### Tool Execution Visualization

Visual feedback for tool execution:

```python
def show_tool_execution(self, tool_name: str, args: Dict):
    \"\"\"Show visual feedback for tool execution\"\"\"
    
    # Create tool execution message
    tool_html = f\"\"\"
    <div class=\"tool-execution\" style=\"
        margin: 8px 0;
        padding: 8px 12px;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 6px;
        font-size: 12px;
        color: #856404;
    \">
        🛠️ Executing: <strong>{tool_name}</strong>
        {f' with {len(args)} parameters' if args else ''}
    </div>
    \"\"\"
    
    # Insert into chat
    cursor = self.chat_display.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertHtml(tool_html)

def show_tool_result(self, tool_name: str, result: Any, success: bool = True):
    \"\"\"Show tool execution result\"\"\"
    
    status_color = \"#d4edda\" if success else \"#f8d7da\"
    text_color = \"#155724\" if success else \"#721c24\"
    icon = \"✅\" if success else \"❌\"
    
    result_html = f\"\"\"
    <div class=\"tool-result\" style=\"
        margin: 4px 0 8px 0;
        padding: 6px 12px;
        background-color: {status_color};
        border-radius: 6px;
        font-size: 12px;
        color: {text_color};
    \">
        {icon} <strong>{tool_name}</strong> completed
        {f': {str(result)[:100]}...' if len(str(result)) > 100 else f': {str(result)}'}
    </div>
    \"\"\"
    
    cursor = self.chat_display.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertHtml(result_html)
```

## Integration Features

### System Integration

```python
def setup_system_integration(self):
    \"\"\"Setup system-level integration features\"\"\"
    
    # Global hotkey for quick access
    self.setup_global_hotkey()
    
    # Clipboard monitoring
    self.setup_clipboard_monitoring()
    
    # File association for supported formats
    self.register_file_associations()

def setup_global_hotkey(self):
    \"\"\"Setup global hotkey (Ctrl+Shift+S) to show SOFIA\"\"\"
    try:
        import keyboard
        
        def show_sofia():
            self.show()
            self.raise_()
            self.activateWindow()
            self.input_field.setFocus()
        
        keyboard.add_hotkey('ctrl+shift+s', show_sofia)
        
    except ImportError:
        print(\"Keyboard library not available - global hotkey disabled\")

def setup_clipboard_monitoring(self):
    \"\"\"Monitor clipboard for automatic image processing\"\"\"
    clipboard = QApplication.clipboard()
    clipboard.dataChanged.connect(self.handle_clipboard_change)

def handle_clipboard_change(self):
    \"\"\"Handle clipboard content changes\"\"\"
    clipboard = QApplication.clipboard()
    mime_data = clipboard.mimeData()
    
    if mime_data.hasImage():
        # Handle image from clipboard
        image = clipboard.image()
        if not image.isNull():
            # Save temporary image
            temp_path = f\"/tmp/sofia_clipboard_{int(time.time())}.png\"
            image.save(temp_path)
            
            # Show notification
            self.show_clipboard_notification(\"Image copied - drop here to analyze\")
            
            # Store for potential use
            self.clipboard_image_path = temp_path
```

### Configuration Management

```python
def load_app_settings(self):
    \"\"\"Load application-specific settings\"\"\"
    settings = QSettings()
    
    # Window geometry
    geometry = settings.value(\"geometry\")
    if geometry:
        self.restoreGeometry(geometry)
    
    # Window state
    state = settings.value(\"windowState\")
    if state:
        self.restoreState(state)
    
    # Theme preferences
    self.theme = settings.value(\"theme\", \"light\")
    self.apply_theme(self.theme)
    
    # Font settings
    font_family = settings.value(\"fontFamily\", \"Segoe UI\")
    font_size = int(settings.value(\"fontSize\", 14))
    self.set_font_preferences(font_family, font_size)

def save_app_settings(self):
    \"\"\"Save application settings on exit\"\"\"
    settings = QSettings()
    settings.setValue(\"geometry\", self.saveGeometry())
    settings.setValue(\"windowState\", self.saveState())
    settings.setValue(\"theme\", self.theme)
    
def closeEvent(self, event):
    \"\"\"Handle application close event\"\"\"
    # Save settings
    self.save_app_settings()
    
    # Minimize to tray instead of closing
    if self.tray_icon and self.tray_icon.isVisible():
        self.hide()
        event.ignore()
        
        # Show tray message
        self.tray_icon.showMessage(
            \"SOFIA\",
            \"Application minimized to tray\",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    else:
        event.accept()
```

## Performance Optimization

### Memory Management

```python
def optimize_chat_history(self):
    \"\"\"Optimize chat display for performance\"\"\"
    
    # Limit number of messages in display
    max_messages = 100
    
    if self.chat_display.document().blockCount() > max_messages:
        # Remove old messages from display
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # Select and delete first 20 messages
        for _ in range(20):
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # Remove newline

def cleanup_temporary_files(self):
    \"\"\"Clean up temporary image files\"\"\"
    temp_dir = Path(\"/tmp\")
    
    # Remove old SOFIA temporary files
    for temp_file in temp_dir.glob(\"sofia_*\"):
        try:
            if temp_file.is_file():
                # Remove files older than 1 hour
                if time.time() - temp_file.stat().st_mtime > 3600:
                    temp_file.unlink()
        except Exception as e:
            print(f\"Error cleaning up {temp_file}: {e}\")
```

### Threading Optimization

```python
def manage_analysis_threads(self):
    \"\"\"Manage background processing threads\"\"\"
    
    # Limit concurrent threads
    max_threads = 2
    
    if hasattr(self, 'active_threads'):
        # Clean up finished threads
        self.active_threads = [t for t in self.active_threads if t.isRunning()]
        
        # Limit active threads
        if len(self.active_threads) >= max_threads:
            return False  # Too many active threads
    else:
        self.active_threads = []
    
    return True

def create_analysis_thread(self, prompt: str, image_path: str = None):
    \"\"\"Create new analysis thread with proper management\"\"\"
    
    if not self.manage_analysis_threads():
        QMessageBox.warning(self, \"Busy\", \"Please wait for current analysis to complete.\")
        return
    
    # Create and start thread
    thread = AnalysisThread(
        prompt=prompt,
        image_path=image_path,
        brain=self.brain,
        chat_messages=self.messages,
        tools=self.tools
    )
    
    # Connect signals
    thread.streaming_chunk.connect(self.handle_streaming_chunk)
    thread.streaming_finished.connect(self.handle_streaming_finished)
    thread.response_received.connect(self.handle_error_response)
    
    # Start thread
    thread.start()
    self.active_threads.append(thread)
```

## Testing

### Unit Tests

```python
def test_message_formatting():
    \"\"\"Test message HTML formatting\"\"\"
    window = ChatWindow(mock_brain, [], [])
    
    html = window.format_message_html(\"user\", \"Test message\", \"12:34\")
    assert \"user-message\" in html
    assert \"Test message\" in html
    assert \"12:34\" in html

def test_drag_drop_validation():
    \"\"\"Test drag and drop file validation\"\"\"
    window = ChatWindow(mock_brain, [], [])
    
    assert window.is_image_file(\"test.png\") == True
    assert window.is_image_file(\"test.jpg\") == True
    assert window.is_image_file(\"test.txt\") == False
```

### Integration Tests

```python
def test_complete_chat_flow():
    \"\"\"Test complete chat interaction\"\"\"
    app = QApplication([])
    window = ChatWindow(mock_brain, [], [])
    
    # Simulate user input
    window.input_field.setText(\"Hello SOFIA\")
    window.send_message()
    
    # Wait for response
    QTest.qWait(1000)
    
    # Verify message was added
    assert len(window.messages) > 0
    assert window.messages[-1]['content'] == \"Hello SOFIA\"
```

The Desktop Application provides a comprehensive, native interface for SOFIA with advanced features for productivity and seamless AI interaction.