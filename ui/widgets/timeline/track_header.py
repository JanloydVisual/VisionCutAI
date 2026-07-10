from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt


class TrackHeader(QLabel):

    def __init__(self, name, parent=None):
        super().__init__(name, parent)

        self.setFixedWidth(120)
        self.setFixedHeight(60)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("""
            background:#2B2B2B;
            color:white;
            border-right:1px solid #555;
            border-bottom:1px solid #444;
            font-weight:bold;
        """)
