"""
PlaybackControls
----------------
Play / Pause / Stop buttons only. Emits signals - never calls
VideoEngine or Controller directly.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal


class PlaybackControls(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

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

        self.play_button.clicked.connect(self.play_clicked.emit)
        self.pause_button.clicked.connect(self.pause_clicked.emit)
        self.stop_button.clicked.connect(self.stop_clicked.emit)

    def set_playing_state(self, is_playing: bool) -> None:
        self.play_button.setEnabled(not is_playing)
        self.pause_button.setEnabled(is_playing)

    def set_controls_enabled(self, enabled: bool) -> None:
        self.play_button.setEnabled(enabled)
        self.pause_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
