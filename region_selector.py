from PyQt6.QtWidgets import QWidget, QRubberBand
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QScreen, QGuiApplication
import mss


class RegionSelector(QWidget):
    region_selected = pyqtSignal(int, int, int, int)  # x, y, width, height
    
    def __init__(self):
        super().__init__()
        self.rubberband = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.initUI()
        
    def initUI(self):
        # Full screen transparent overlay
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.3)
        
        # Cover all screens
        screens = QGuiApplication.screens()
        if screens:
            # Get combined geometry of all screens
            total_rect = screens[0].geometry()
            for screen in screens[1:]:
                total_rect = total_rect.united(screen.geometry())
            
            self.setGeometry(total_rect)
        
        self.setCursor(Qt.CursorShape.CrossCursor)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 50))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = QPoint(event.pos())
            self.rubberband.setGeometry(QRect(self.origin, QPoint()))
            self.rubberband.show()
    
    def mouseMoveEvent(self, event):
        if self.rubberband.isVisible():
            self.rubberband.setGeometry(QRect(self.origin, event.pos()).normalized())
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rubberband.isVisible():
            self.rubberband.hide()
            
            # Get selected region
            rect = self.rubberband.geometry()
            x = self.x() + rect.x()
            y = self.y() + rect.y()
            
            # Emit the selected region
            self.region_selected.emit(x, y, rect.width(), rect.height())
            
            # Close selector
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()