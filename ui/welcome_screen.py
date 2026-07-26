from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QStyle
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent

class WelcomeScreen(QWidget):
    open_project_requested = pyqtSignal()
    import_video_requested = pyqtSignal(str) # Emits file path for drag and drop
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #181818; color: #E6E6E6;")
        self.setAcceptDrops(True)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
        lbl_title = QLabel("VisionCut AI")
        lbl_title.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        # Subtitle
        lbl_subtitle = QLabel("AI Rotoscope & Background Studio")
        lbl_subtitle.setFont(QFont("Segoe UI", 16))
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitle.setStyleSheet("color: #A0A0A0;")
        layout.addWidget(lbl_subtitle)
        
        layout.addSpacing(50)
        
        # Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(30)
        
        # Primary Import Video Button
        self.btn_import = QPushButton("+ Import Video")
        self.btn_import.setMinimumSize(220, 60)
        self.btn_import.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.btn_import.setStyleSheet("""
            QPushButton {
                background-color: #35D07F;
                color: #181818;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45E08F;
            }
        """)
        self.btn_import.clicked.connect(lambda: self.import_video_requested.emit("")) # Empty string means open dialog
        
        # Secondary Open Project Button
        self.btn_open = QPushButton("Open Project")
        self.btn_open.setMinimumSize(220, 60)
        self.btn_open.setFont(QFont("Segoe UI", 14))
        self.btn_open.setStyleSheet("""
            QPushButton {
                background-color: #2A2A2A;
                color: #E6E6E6;
                border: 1px solid #3A3A3A;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #4A4A4A;
            }
        """)
        self.btn_open.clicked.connect(self.open_project_requested.emit)
        
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_open)
        
        layout.addLayout(btn_layout)
        
        layout.addSpacing(40)
        
        # Drag and drop hint
        self.lbl_drop_hint = QLabel("Or drag and drop a video file here")
        self.lbl_drop_hint.setFont(QFont("Segoe UI", 12))
        self.lbl_drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_drop_hint.setStyleSheet("color: #666666;")
        layout.addWidget(self.lbl_drop_hint)
        
        layout.addSpacing(60)
        
        # Recent Projects Section
        recent_frame = QFrame()
        recent_frame.setStyleSheet("""
            QFrame {
                background-color: #222222;
                border: 1px solid #3A3A3A;
                border-radius: 12px;
            }
        """)
        recent_frame.setMaximumWidth(600)
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_recent = QLabel("Recent Projects")
        lbl_recent.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_recent.setStyleSheet("border: none;")
        recent_layout.addWidget(lbl_recent)
        
        lbl_none = QLabel("No recent projects found.")
        lbl_none.setFont(QFont("Segoe UI", 11))
        lbl_none.setStyleSheet("color: #888888; border: none;")
        recent_layout.addWidget(lbl_none)
        
        layout.addWidget(recent_frame, alignment=Qt.AlignmentFlag.AlignHCenter)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self.lbl_drop_hint.setStyleSheet("color: #35D07F; font-weight: bold;")
            event.acceptProposedAction()
            
    def dragLeaveEvent(self, event):
        self.lbl_drop_hint.setStyleSheet("color: #666666; font-weight: normal;")
            
    def dropEvent(self, event: QDropEvent):
        self.lbl_drop_hint.setStyleSheet("color: #666666; font-weight: normal;")
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            self.import_video_requested.emit(file_path)
