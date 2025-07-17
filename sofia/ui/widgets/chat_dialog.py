from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLineEdit, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut


class ChatDialog(QDialog):
    message_submitted = pyqtSignal(str)
    
    def __init__(self, parent=None, initial_prompt="What would you like to know about this screenshot?"):
        super().__init__(parent)
        self.initUI(initial_prompt)
        
    def initUI(self, initial_prompt):
        self.setWindowTitle('Ask SOFIA')
        self.setFixedSize(500, 200)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Prompt label
        prompt_label = QLabel(initial_prompt)
        prompt_label.setWordWrap(True)
        prompt_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 14px;
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
            }
        """)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your question here...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #ddd;
                border-radius: 5px;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
            }
        """)
        self.input_field.returnPressed.connect(self.submit_message)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Analyze button
        self.analyze_btn = QPushButton('Analyze')
        self.analyze_btn.clicked.connect(self.submit_message)
        self.analyze_btn.setDefault(True)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        
        # Cancel button
        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.analyze_btn)
        
        # Add to main layout
        layout.addWidget(prompt_label)
        layout.addWidget(self.input_field)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Focus input field
        self.input_field.setFocus()
        
        # Escape key to cancel
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self.reject)
    
    def submit_message(self):
        text = self.input_field.text().strip()
        if text:
            self.message_submitted.emit(text)
            self.accept()
    
    def get_message(self):
        return self.input_field.text().strip()