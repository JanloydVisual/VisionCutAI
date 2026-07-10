from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt


class TimelineTrack(QWidget):

    TRACK_HEIGHT = 50

    def __init__(self, track, parent=None):
        super().__init__(parent)

        self.track = track

        self.setMinimumHeight(self.TRACK_HEIGHT)

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            QColor(45, 45, 45)
        )

        painter.setPen(Qt.GlobalColor.white)

        painter.drawText(
            10,
            30,
            self.track.name
        )
