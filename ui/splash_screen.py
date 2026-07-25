import time
from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt

class ModernSplashScreen(QSplashScreen):
    def __init__(self, version):
        # Create a simple dark background with text for the splash (no external image required)
        pixmap = QPixmap(600, 350)
        pixmap.fill(QColor("#1e1e1e"))
        
        painter = QPainter(pixmap)
        
        # Title
        painter.setPen(QColor("#ffffff"))
        font = QFont("Inter", 32, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "VisionCut AI")
        
        # Version
        painter.setPen(QColor("#888888"))
        font_ver = QFont("Inter", 12)
        painter.setFont(font_ver)
        painter.drawText(0, 200, 600, 50, Qt.AlignmentFlag.AlignCenter, f"Version {version}")
        
        painter.end()
        
        super().__init__(pixmap)
        
        self.message_color = QColor("#5dade2")
        self.showMessage("Initializing...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, self.message_color)

    def set_progress(self, message: str, delay=0.5):
        self.showMessage(message, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, self.message_color)
        QApplication.processEvents()
        time.sleep(delay)  # Small delay just to let the user see the progress nicely
