"""
Cancel Export Dialog
-------------------
Confirmation dialog for cancelling an export.
Asks whether to keep or delete the partially exported frames.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
)
from PyQt6.QtCore import Qt


class CancelExportDialog(QDialog):
    """Dialog to confirm export cancellation."""

    def __init__(self, parent=None, is_video: bool = True):
        super().__init__(parent)

        self.keep_frames = True  # Default to keeping frames
        self.is_video = is_video

        self.setWindowTitle("Cancel Export")
        self.setModal(True)
        self.resize(350, 150)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Question
        if self.is_video:
            question = QLabel("Cancel video export? This may leave a corrupted output file.")
        else:
            question = QLabel("Cancel export? Choose what to do with exported frames:")

        question.setStyleSheet("color: #ddd; font-size: 14px;")
        question.setWordWrap(True)
        layout.addWidget(question)

        # Options for PNG sequence
        if not self.is_video:
            self.keep_button = QPushButton("Keep exported frames")
            self.delete_button = QPushButton("Delete incomplete export")

            self.keep_button.setCheckable(True)
            self.delete_button.setCheckable(True)
            self.keep_button.setChecked(True)

            self.button_group = QButtonGroup(self)
            self.button_group.addButton(self.keep_button)
            self.button_group.addButton(self.delete_button)

            layout.addWidget(self.keep_button)
            layout.addWidget(self.delete_button)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Continue Export")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.confirm_button = QPushButton("Cancel Export")
        self.confirm_button.setDefault(True)
        self.confirm_button.clicked.connect(self._on_confirm)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #cc3333;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff4444;
            }
        """)
        button_layout.addWidget(self.confirm_button)

        layout.addLayout(button_layout)

    def _on_confirm(self):
        """Handle confirm button click."""
        if not self.is_video:
            self.keep_frames = self.keep_button.isChecked()
        self.accept()

    def get_keep_frames(self) -> bool:
        """Return whether to keep exported frames."""
        return self.keep_frames