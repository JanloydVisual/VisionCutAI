"""
Export Complete Dialog
--------------------
Shows export completion with Open Output Folder and Close buttons.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import Qt
import os
import subprocess


class ExportCompleteDialog(QDialog):
    """Dialog shown after successful export completion."""

    def __init__(self, parent=None, output_path: str = ""):
        super().__init__(parent)
        self.output_path = output_path

        self.setWindowTitle("Export Complete")
        self.setModal(True)
        self.resize(350, 150)
        self.setMinimumWidth(300)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Success icon and message
        success_layout = QHBoxLayout()
        success_icon = QLabel("✓")
        success_icon.setStyleSheet("font-size: 32px; color: #2d7d46;")
        success_layout.addWidget(success_icon)

        message_layout = QVBoxLayout()
        title = QLabel("Export Complete")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ddd;")
        message_layout.addWidget(title)

        if self.output_path:
            path_label = QLabel(f"Output: {self.output_path}")
            path_label.setStyleSheet("color: #888; font-size: 11px;")
            path_label.setWordWrap(True)
            message_layout.addWidget(path_label)

        success_layout.addLayout(message_layout)
        layout.addLayout(success_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: #ddd;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        button_layout.addWidget(self.close_button)

        self.open_folder_button = QPushButton("Open Output Folder")
        self.open_folder_button.clicked.connect(self._open_folder)
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background-color: #2d7d46;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a9d5a;
            }
        """)
        button_layout.addWidget(self.open_folder_button)

        layout.addLayout(button_layout)

    def _open_folder(self):
        """Open the output folder in file explorer."""
        if self.output_path and os.path.exists(self.output_path):
            folder = self.output_path
        else:
            folder = os.path.dirname(self.output_path) if self.output_path else ""

        if folder and os.path.exists(folder):
            try:
                subprocess.run(["explorer", "/select,", os.path.normpath(folder)], shell=True)
            except Exception:
                subprocess.run(["explorer", os.path.normpath(folder)], shell=True)
        self.accept()