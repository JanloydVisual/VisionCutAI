from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QStyle

class WelcomeScreen(QWidget):
    open_project_requested = pyqtSignal()
    import_video_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
        lbl_title = QLabel("VisionCut AI")
        lbl_title.setFont(QFont("Inter", 48, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        layout.addSpacing(40)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(20)
        
        self.btn_open = QPushButton("Open Project")
        self.btn_open.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.btn_open.setMinimumSize(180, 50)
        self.btn_open.setFont(QFont("Inter", 12))
        self.btn_open.clicked.connect(self.open_project_requested.emit)
        
        self.btn_import = QPushButton("Import Video")
        self.btn_import.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_import.setMinimumSize(180, 50)
        self.btn_import.setFont(QFont("Inter", 12))
        self.btn_import.clicked.connect(self.import_video_requested.emit)
        
        btn_layout.addWidget(self.btn_open)
        btn_layout.addWidget(self.btn_import)
        
        layout.addLayout(btn_layout)
        
        layout.addSpacing(40)
        
        # Recent Projects placeholder
        lbl_recent = QLabel("Recent Projects")
        lbl_recent.setFont(QFont("Inter", 16))
        lbl_recent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_recent.setStyleSheet("color: #888888;")
        layout.addWidget(lbl_recent)
        
        lbl_none = QLabel("No recent projects found.")
        lbl_none.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_none.setStyleSheet("color: #555555;")
        layout.addWidget(lbl_none)
