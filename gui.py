from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
)

from preview_engine import PreviewEngine
from controller import AppController
from config import APP_NAME
from gpu_manager import GPUManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.controller = AppController()

        self.setWindowTitle(APP_NAME)
        self.resize(1200, 700)

        # =========================
        # Main Layout
        # =========================

        main_layout = QVBoxLayout()

        # -------------------------
        # Top Bar
        # -------------------------

        self.file_label = QLabel("No video selected")

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.open_video)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.file_label)
        top_layout.addStretch()
        top_layout.addWidget(self.browse_button)

        # -------------------------
        # Preview
        # -------------------------

        self.preview = QLabel("Video Preview")
        self.preview.setMinimumHeight(500)
        self.preview.setStyleSheet("""
            QLabel{
                border:2px solid #555;
                font-size:22px;
                color:white;
                background:#222;
            }
        """)
        self.preview.setAlignment(
            __import__("PyQt6.QtCore").QtCore.Qt.AlignmentFlag.AlignCenter
        )

        # -------------------------
        # GPU Information
        # -------------------------

        gpu = GPUManager.get_gpu_info()

        if gpu["available"]:
            gpu_text = f"GPU : {gpu['name']}"
        else:
            gpu_text = "GPU : Not Available"

        self.gpu_label = QLabel(gpu_text)

        # -------------------------
        # Status
        # -------------------------

        self.status = QLabel("Status : Ready")

        # -------------------------
        # Buttons
        # -------------------------

        self.remove_button = QPushButton("Remove Background")
        self.remove_button.setEnabled(False)

        # -------------------------
        # Add Widgets
        # -------------------------

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.preview)
        main_layout.addWidget(self.gpu_label)
        main_layout.addWidget(self.status)
        main_layout.addWidget(self.remove_button)

        container = QWidget()
        container.setLayout(main_layout)

        self.setCentralWidget(container)

    def open_video(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Videos (*.mp4 *.mov *.avi)"
        )

        if not filename:
            return

        info = self.controller.open_video(filename)

        self.file_label.setText(filename)

        self.status.setText(
            f"Loaded | "
            f"{info['Width']} x {info['Height']} | "
            f"{info['FPS']:.2f} FPS"
        )

        self.remove_button.setEnabled(True)