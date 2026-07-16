"""
TrackHeaderColumn
------------------
Fixed-position column showing track names (Video Track 1, Audio
Track 1, ...). Sits to the left of the scrollable TimelineCanvas,
outside the QScrollArea, so it stays visible while the canvas
scrolls horizontally. Row geometry mirrors TimelineCanvas exactly
so labels stay aligned with their tracks.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QRect

from ui.widgets.timeline.timeline_canvas import (
    TRACK_LABEL_WIDTH,
    TRACK_HEIGHT,
    TRACK_GAP,
    TRACK_START_Y,
    RULER_HEIGHT,
)


class TrackHeaderColumn(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeline = None
        self.setFixedWidth(TRACK_LABEL_WIDTH)
        self.setMinimumHeight(150)

    def set_timeline(self, timeline) -> None:
        self.timeline = timeline
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(36, 36, 36))

        if self.timeline is None:
            return

        label_font = QFont()
        label_font.setBold(True)
        label_font.setPointSize(9)
        painter.setFont(label_font)

        y = TRACK_START_Y
        for track in self.timeline.tracks:
            painter.fillRect(0, y, TRACK_LABEL_WIDTH, TRACK_HEIGHT, QColor(43, 43, 43))
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.drawLine(TRACK_LABEL_WIDTH - 1, y, TRACK_LABEL_WIDTH - 1, y + TRACK_HEIGHT)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                QRect(8, y, TRACK_LABEL_WIDTH - 12, TRACK_HEIGHT),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                track.name,
            )
            y += TRACK_HEIGHT + TRACK_GAP
