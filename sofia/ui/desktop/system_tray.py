from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon


class SystemTrayManager:
    """Manages system tray functionality for the chat window"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.tray_icon = None
        self.setup_tray()
    
    def setup_tray(self):
        """Initialize system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self.parent_window)
        self.tray_icon.setIcon(QIcon.fromTheme('applications-system'))

        tray_menu = QMenu()

        show_action = QAction("Show/Hide", self.parent_window)
        show_action.triggered.connect(self.parent_window.toggle_visibility)

        exit_action = QAction("Exit", self.parent_window)
        exit_action.triggered.connect(self.parent_window.close)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def hide(self):
        """Hide the system tray icon"""
        if self.tray_icon:
            self.tray_icon.hide()