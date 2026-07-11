"""
TimelineRuler
-------------
Fixed timeline ruler that stays visible while the canvas scrolls.
Draws time markings synchronized with TimelineCanvas coordinates.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt


# Match TimelineCanvas constants
PIXELS_PER_FRAME = 2
TRACK_LABEL_WIDTH = 140
RULER_HEIGHT = 30


class TimelineRuler(QWidget):
    """
    Fixed ruler widget that displays time markings.
    Sits above the scroll area and stays visible while content scrolls.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.fps = 30.0
        self._scroll_offset = 0  # Horizontal scroll offset from QScrollArea

        self.setFixedHeight(RULER_HEIGHT)

        # Styling
        self.setStyleSheet("background-color: #303030;")

    def set_fps(self, fps: float) -> None:
        """Update FPS for time label calculations."""
        self.fps = fps if fps and fps > 0 else 30.0
        self.update()

    def set_scroll_offset(self, offset: int) -> None:
        """Update horizontal scroll offset from the scroll area."""
        if offset != self._scroll_offset:
            self._scroll_offset = offset
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(48, 48, 48))

        # Left margin area (track label column)
        painter.fillRect(0, 0, TRACK_LABEL_WIDTH, RULER_HEIGHT, QColor(38, 38, 38))
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(TRACK_LABEL_WIDTH, 0, TRACK_LABEL_WIDTH, RULER_HEIGHT)

        # Calculate visible range based on scroll offset
        start_x = TRACK_LABEL_WIDTH - self._scroll_offset
        width = self.width() - TRACK_LABEL_WIDTH

        # Draw tick marks every 100 pixels (50 frames at PIXELS_PER_FRAME=2)
        tick_spacing = 100
        first_tick = ((self._scroll_offset // tick_spacing) + 1) * tick_spacing

        painter.setPen(QPen(QColor(110, 110, 110)))
        painter.setFont(QFont("monospace", 8))

        for tick_x in range(first_tick, self._scroll_offset + width, tick_spacing):
            screen_x = tick_x - self._scroll_offset + TRACK_LABEL_WIDTH
            if screen_x < TRACK_LABEL_WIDTH:
                continue
            if screen_x > self.width():
                break

            # Tick mark
            painter.drawLine(screen_x, RULER_HEIGHT - 10, screen_x, RULER_HEIGHT)

            # Time label (seconds)
            frame = tick_x / PIXELS_PER_FRAME
            seconds = frame / self.fps if self.fps > 0 else 0
            label = f"{int(seconds)}"
            painter.drawText(screen_x + 4, RULER_HEIGHT - 12, label)

        # Draw minor ticks every 50 pixels (25 frames)
        minor_tick_spacing = 50
        first_minor = ((self._scroll_offset // minor_tick_spacing) + 1) * minor_tick_spacing

        painter.setPen(QPen(QColor(80, 80, 80)))
        for tick_x in range(first_minor, self._scroll_offset + width, minor_tick_spacing):
            screen_x = tick_x - self._scroll_offset + TRACK_LABEL_WIDTH
            if screen_x < TRACK_LABEL_WIDTH:
                continue
            if screen_x > self.width():
                break

            # Only draw minor tick if it's not a major tick
            if tick_x % tick_spacing != 0:
                painter.drawLine(screen_x, RULER_HEIGHT - 5, screen_x, RULER_HEIGHT)
