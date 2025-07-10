import sys
import signal
from PyQt6.QtWidgets import QApplication

from sofia.ui.desktop.chat_window import TransparentChatWindow


def signal_handler(signum, frame):
    """Handle system signals for clean shutdown"""
    QApplication.quit()


def main():
    """Main entry point for the SOFIA desktop application"""
    # Set up signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    window = TransparentChatWindow()
    window.show()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nShutting down SOFIA Desktop...")
        window.close()
        sys.exit(0)


if __name__ == '__main__':
    main()