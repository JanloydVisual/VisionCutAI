"""
OverlayCanvas
-------------
Transparent surface stacked above the video preview.
Future features draw here WITHOUT modifying VideoPreview or
VideoPlayerWidget: AI masks, polygon tools, magic wand selection,
detection boxes, tracking points, safe areas, guides.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt


class OverlayCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
