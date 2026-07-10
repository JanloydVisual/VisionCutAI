"""
VideoPreview
------------
Owns the frame-rendering QLabel and the OverlayCanvas stacked on top.
No playback logic, no controller access - purely visual.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QStackedLayout, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from ui.widgets.overlay_canvas import OverlayCanvas


class VideoPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = QStackedLayout(self)
        self._layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.frame_label = QLabel("No video loaded")
        self.frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_label.setStyleSheet("background-color: black; color: #666;")
        self.frame_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.overlay = OverlayCanvas(self)

        self._layout.addWidget(self.frame_label)
        self._layout.addWidget(self.overlay)

    def load_frame(self, pixmap: QPixmap) -> None:
        if pixmap is None or pixmap.isNull():
            return
        scaled = pixmap.scaled(
            self.frame_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.frame_label.setPixmap(scaled)

    def clear(self) -> None:
        self.frame_label.clear()
        self.frame_label.setText("No video loaded")

    def get_overlay(self) -> OverlayCanvas:
        return self.overlay
