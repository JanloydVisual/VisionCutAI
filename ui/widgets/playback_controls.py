"""
PlaybackControls
----------------
Play / Pause / Stop / Remove Background buttons.
Emits signals - never calls VideoEngine or Controller directly.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal


class PlaybackControls(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    remove_bg_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")

        for btn in (self.play_button, self.pause_button, self.stop_button):
            btn.setMinimumWidth(80)
            layout.addWidget(btn)

        layout.addStretch(1)

        # Remove Background button - primary action, visually distinct
        self.remove_bg_button = QPushButton("Remove Background")
        self.remove_bg_button.setMinimumWidth(140)
        self.remove_bg_button.setEnabled(False)
        self.remove_bg_button.setStyleSheet("""
            QPushButton {
                background-color: #2d7d46;
                color: white;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a9d5a;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        layout.addWidget(self.remove_bg_button)

        self.play_button.clicked.connect(self.play_clicked.emit)
        self.pause_button.clicked.connect(self.pause_clicked.emit)
        self.stop_button.clicked.connect(self.stop_clicked.emit)
        self.remove_bg_button.clicked.connect(self.remove_bg_clicked.emit)

    def set_playing_state(self, is_playing: bool) -> None:
        self.play_button.setEnabled(not is_playing)
        self.pause_button.setEnabled(is_playing)

    def set_controls_enabled(self, enabled: bool) -> None:
        self.play_button.setEnabled(enabled)
        self.pause_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)

    def set_remove_bg_enabled(self, enabled: bool) -> None:
        self.remove_bg_button.setEnabled(enabled)

    def set_remove_bg_text(self, text: str) -> None:
        self.remove_bg_button.setText(text)