"""
TimelineRuler
-------------
Fixed timeline ruler that stays visible while the canvas scrolls.
Draws time markings synchronized with TimelineCanvas coordinates.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QRect, pyqtSignal


# Match TimelineCanvas constants
PIXELS_PER_FRAME = 2
TRACK_LABEL_WIDTH = 140
RULER_HEIGHT = 30
PLAYHEAD_HANDLE_HALF_WIDTH = 8


class TimelineRuler(QWidget):
    """
    Fixed ruler widget that displays time markings.
    Sits above the scroll area and stays visible while content scrolls.
    """

    seek_requested = pyqtSignal(int)
    playhead_dragged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.fps = 30.0
        self._scroll_offset = 0  # Horizontal scroll offset from QScrollArea
        self.playhead_frame = 0
        self._dragging_playhead = False

        self.setFixedHeight(RULER_HEIGHT)

        # Styling
        self.setStyleSheet("background-color: #303030;")
        self.setMouseTracking(True)

    def set_fps(self, fps: float) -> None:
        """Update FPS for time label calculations."""
        self.fps = fps if fps and fps > 0 else 30.0
        self.update()

    def set_render_cache(self, render_cache):
        self.render_cache = render_cache
        if hasattr(self.render_cache, 'cache_updated'):
            self.render_cache.cache_updated.connect(self.update)
        self.update()

    def set_scroll_offset(self, offset: int) -> None:
        """Update horizontal scroll offset from the scroll area."""
        if offset != self._scroll_offset:
            self._scroll_offset = offset
            self.update()

    def set_playhead_frame(self, frame: int) -> None:
        self.playhead_frame = max(0, frame)
        self.update()

    def _timeline_frame_at(self, x: int) -> int:
        return max(0, int((x + self._scroll_offset) / PIXELS_PER_FRAME))

    def _playhead_x(self) -> int:
        return int(self.playhead_frame * PIXELS_PER_FRAME) - self._scroll_offset

    def _playhead_handle_rect(self):
        phx = self._playhead_x()
        return QRect(
            phx - PLAYHEAD_HANDLE_HALF_WIDTH,
            0,
            PLAYHEAD_HANDLE_HALF_WIDTH * 2,
            RULER_HEIGHT,
        )

    def _playhead_hit_test(self, x, y):
        return self._playhead_handle_rect().contains(x, y)

    def mousePressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        
        pos = event.position()
        x, y = int(pos.x()), int(pos.y())
        
        if self._playhead_hit_test(x, y):
            self._dragging_playhead = True
            target_frame = self._timeline_frame_at(x)
            if target_frame != self.playhead_frame:
                self.playhead_dragged.emit(target_frame)
            event.accept()
            return
            
        # Clicked ruler body
        self.seek_requested.emit(self._timeline_frame_at(x))
        event.accept()

    def mouseMoveEvent(self, event):
        from PyQt6.QtCore import Qt
        x, y = int(event.position().x()), int(event.position().y())
        
        if self._dragging_playhead:
            target_frame = self._timeline_frame_at(x)
            if target_frame != self.playhead_frame:
                self.playhead_dragged.emit(target_frame)
            event.accept()
            return
            
        was_hovering = getattr(self, '_hovering_playhead', False)
        self._hovering_playhead = self._playhead_hit_test(x, y)
        if was_hovering != self._hovering_playhead:
            from PyQt6.QtGui import QCursor
            if self._hovering_playhead:
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging_playhead:
                self._dragging_playhead = False
                from PyQt6.QtGui import QCursor
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(48, 48, 48))

        # This widget's local x=0 already lines up with canvas content
        # x=0 (TrackHeaderColumn lives outside this widget, in its own
        # fixed column) so no TRACK_LABEL_WIDTH offset belongs in here.
        width = self.width()

        # Draw tick marks every 100 pixels (50 frames at PIXELS_PER_FRAME=2)
        tick_spacing = 100
        first_tick = ((self._scroll_offset // tick_spacing) + 1) * tick_spacing

        painter.setPen(QPen(QColor(110, 110, 110)))
        painter.setFont(QFont("monospace", 8))

        for tick_x in range(first_tick, self._scroll_offset + width, tick_spacing):
            screen_x = tick_x - self._scroll_offset
            if screen_x < 0:
                continue
            if screen_x > width:
                break

            # Tick mark
            painter.drawLine(int(screen_x), RULER_HEIGHT - 10, int(screen_x), RULER_HEIGHT)

            # Time label (seconds)
            frame = tick_x / PIXELS_PER_FRAME
            seconds = frame / self.fps if self.fps > 0 else 0
            label = f"{int(seconds)}"
            painter.drawText(int(screen_x + 4), RULER_HEIGHT - 12, label)

        # Draw minor ticks every 50 pixels (25 frames)
        minor_tick_spacing = 50
        first_minor = ((self._scroll_offset // minor_tick_spacing) + 1) * minor_tick_spacing

        painter.setPen(QPen(QColor(80, 80, 80)))
        for tick_x in range(first_minor, self._scroll_offset + width, minor_tick_spacing):
            screen_x = tick_x - self._scroll_offset
            if screen_x < 0:
                continue
            if screen_x > width:
                break

            # Only draw minor tick if it's not a major tick
            if tick_x % tick_spacing != 0:
                painter.drawLine(int(screen_x), RULER_HEIGHT - 5, int(screen_x), RULER_HEIGHT)

        # Draw render cache bar
        if getattr(self, 'render_cache', None):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(76, 175, 80))  # Green bar
            
            start_frame = int(self._scroll_offset / PIXELS_PER_FRAME)
            end_frame = int((self._scroll_offset + width) / PIXELS_PER_FRAME) + 1
            
            # Group consecutive cached frames to minimize draw calls
            rects_to_draw = []
            current_start = None
            
            for f in range(start_frame, end_frame):
                if self.render_cache.has_frame(f):
                    if current_start is None:
                        current_start = f
                else:
                    if current_start is not None:
                        rects_to_draw.append((current_start, f - 1))
                        current_start = None
                        
            if current_start is not None:
                rects_to_draw.append((current_start, end_frame - 1))
                
            for start, end in rects_to_draw:
                x = int(start * PIXELS_PER_FRAME) - self._scroll_offset
                w = int((end - start + 1) * PIXELS_PER_FRAME)
                painter.drawRect(x, RULER_HEIGHT - 3, w, 3)

        # Draw playhead handle
        handle_rect = self._playhead_handle_rect()
        painter.setBrush(QColor(255, 60, 60))
        painter.setPen(QPen(QColor(200, 40, 40), 1))
        painter.drawRect(handle_rect)

        painter.setPen(QPen(QColor(255, 200, 200), 1))
        mid_x = handle_rect.center().x()
        handle_top = handle_rect.top() + 6
        for offset in range(3):
            left = mid_x - 4 + offset * 3
            right = mid_x + 4 - offset * 3
            y_pos = handle_top + offset * 4
            painter.drawLine(left, y_pos, right, y_pos)
