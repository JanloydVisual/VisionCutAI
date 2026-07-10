from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt


class TimelinePlayhead(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.frame = 0

    def set_frame(self, frame):

        self.frame = frame
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        pen = QPen(QColor(255, 80, 80))
        pen.setWidth(2)

        painter.setPen(pen)

        x = self.width() // 2

        painter.drawLine(
            x,
            0,
            x,
            self.height()
        )
