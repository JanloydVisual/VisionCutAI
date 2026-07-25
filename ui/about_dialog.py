import sys
import platform
import cv2
import onnxruntime as ort
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from version import __version__, __app_name__

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {__app_name__}")
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #2b2b2b; color: #d4d4d4;")
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel(__app_name__)
        lbl_title.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        lbl_ver = QLabel(f"Version {__version__}")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_ver)
        
        layout.addSpacing(10)
        
        system_info = (
            f"System: {platform.system()} {platform.release()}\n"
            f"Python: {sys.version.split(' ')[0]}\n"
            f"ONNX Runtime: {ort.__version__}\n"
            f"OpenCV: {cv2.__version__}\n"
        )
        
        text_info = QTextEdit()
        text_info.setReadOnly(True)
        text_info.setStyleSheet("background-color: #1e1e1e; font-family: Consolas; font-size: 11px;")
        text_info.setPlainText(system_info)
        layout.addWidget(text_info)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
