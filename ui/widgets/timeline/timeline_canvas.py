from pathlib import Path

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QMouseEvent, QFont, QCursor
from PyQt6.QtCore import Qt, QRect, pyqtSignal


PIXELS_PER_FRAME = 2
TRACK_HEIGHT = 60
TRACK_GAP = 10
TRACK_START_Y = 40
TRACK_LABEL_WIDTH = 140
RULER_HEIGHT = 30
TRIM_HANDLE_WIDTH = 8
PLAYHEAD_HANDLE_HALF_WIDTH = 8    # Half-width of the red handle (total 16px)
PLAYHEAD_HANDLE_HEIGHT = 22        # Height of the clickable grab area at the top


class TimelineCanvas(QWidget):
    ruler_clicked = pyqtSignal(int)
    clip_selected = pyqtSignal(object)
    clip_move_requested = pyqtSignal(object, int)
    clip_trim_requested = pyqtSignal(object, str, int)
    clip_edit_started = pyqtSignal()
    clip_edit_finished = pyqtSignal()
    # Professional editing signals
    split_at_frame = pyqtSignal(int)
    playhead_dragged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.timeline = None
        self.playhead_frame = 0
        self.fps = 30.0
        self.selected_clip = None
        self.blade_mode = False

        self.dragging_clip = None
        self.drag_mode = None
        self.drag_start_x = 0
        self.drag_start_frame = 0

        # Playhead dragging
        self._dragging_playhead = False
        self._hovering_playhead = False

        self.setMinimumSize(4000, 300)
        self.setMouseTracking(True)  # Enable mouse tracking for hover detection
        self._update_cursor()

    def set_blade_mode(self, enabled: bool) -> None:
        self.blade_mode = enabled
        self._update_cursor()

    def _update_cursor(self) -> None:
        if self._dragging_playhead:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif self._hovering_playhead:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif self.blade_mode:
            self.setCursor(QCursor(Qt.CursorShape.SplitHCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def set_timeline(self, timeline):
        self.timeline = timeline
        self.refresh()

    def refresh(self):
        self.selected_clip = (
            self.timeline.get_selected_clip()
            if self.timeline is not None
            else None
        )
        self.update()

    def set_fps(self, fps):
        self.fps = fps if fps and fps > 0 else 30.0
        self.update()

    def set_playhead_frame(self, frame):
        self.playhead_frame = max(0, frame)
        self.update()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clip_rect(clip, track_y):
        x = TRACK_LABEL_WIDTH + clip.timeline_start_frame * PIXELS_PER_FRAME
        width = max(2, clip.frame_count * PIXELS_PER_FRAME)
        return QRect(int(x), track_y + 8, int(width), 44)

    def _timeline_frame_at(self, x):
        return max(0, int((x - TRACK_LABEL_WIDTH) / PIXELS_PER_FRAME))

    def _playhead_x(self):
        return TRACK_LABEL_WIDTH + self.playhead_frame * PIXELS_PER_FRAME

    def _playhead_handle_rect(self):
        """QRect of the top red handle grab area."""
        phx = self._playhead_x()
        return QRect(
            phx - PLAYHEAD_HANDLE_HALF_WIDTH,
            0,
            PLAYHEAD_HANDLE_HALF_WIDTH * 2,
            PLAYHEAD_HANDLE_HEIGHT,
        )

    def _playhead_hit_test(self, x, y):
        """Returns True if (x, y) is inside the red playhead handle area (top of line)."""
        return self._playhead_handle_rect().contains(x, y)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def _draw_track_background(self, painter, y, track):
        """Draw the track background row and its label in the left margin."""
        # Track background
        painter.fillRect(
            TRACK_LABEL_WIDTH, y, self.width(), TRACK_HEIGHT, QColor(58, 58, 58)
        )
        # Track label area (left margin)
        painter.fillRect(
            0, y, TRACK_LABEL_WIDTH, TRACK_HEIGHT, QColor(43, 43, 43)
        )
        # Separator line between label and track content
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(TRACK_LABEL_WIDTH, y, TRACK_LABEL_WIDTH, y + TRACK_HEIGHT)

        # Track name label
        painter.setPen(Qt.GlobalColor.white)
        label_font = QFont()
        label_font.setBold(True)
        label_font.setPointSize(9)
        painter.setFont(label_font)
        painter.drawText(
            QRect(8, y, TRACK_LABEL_WIDTH - 12, TRACK_HEIGHT),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            track.name,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(36, 36, 36))

        # -- Ruler area --
        painter.fillRect(0, 0, self.width(), RULER_HEIGHT, QColor(48, 48, 48))
        painter.fillRect(0, 0, TRACK_LABEL_WIDTH, RULER_HEIGHT, QColor(38, 38, 38))
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(TRACK_LABEL_WIDTH, 0, TRACK_LABEL_WIDTH, RULER_HEIGHT)

        # Ruler tick marks and time labels
        painter.setPen(QPen(QColor(110, 110, 110)))
        for x in range(TRACK_LABEL_WIDTH, self.width(), 100):
            painter.drawLine(x, 0, x, RULER_HEIGHT)
            frame = (x - TRACK_LABEL_WIDTH) / PIXELS_PER_FRAME
            painter.drawText(x + 4, 20, f"{int(frame / self.fps):02}")

        if self.timeline is None:
            return

        # -- Track rows --
        y = TRACK_START_Y
        for track in self.timeline.tracks:
            self._draw_track_background(painter, y, track)

            for clip in track.clips:
                rect = self._clip_rect(clip, y)
                painter.fillRect(rect, QColor(70, 120, 220))

                if clip == self.selected_clip:
                    painter.setPen(QPen(QColor(255, 215, 0), 3))
                else:
                    painter.setPen(Qt.GlobalColor.white)

                painter.drawRect(rect)
                painter.drawText(
                    rect.adjusted(10, 0, -10, 0),
                    Qt.AlignmentFlag.AlignVCenter,
                    Path(clip.source_path).name,
                )

                if clip == self.selected_clip:
                    painter.fillRect(
                        QRect(rect.left(), rect.top(), TRIM_HANDLE_WIDTH, rect.height()),
                        QColor(255, 215, 0),
                    )
                    painter.fillRect(
                        QRect(
                            rect.right() - TRIM_HANDLE_WIDTH + 1,
                            rect.top(),
                            TRIM_HANDLE_WIDTH,
                            rect.height(),
                        ),
                        QColor(255, 215, 0),
                    )

            y += TRACK_HEIGHT + TRACK_GAP

        # -- Playhead: thin vertical red line down the entire height --
        playhead_x = self._playhead_x()
        painter.setPen(QPen(QColor(255, 60, 60), 2))
        painter.drawLine(playhead_x, PLAYHEAD_HANDLE_HEIGHT, playhead_x, self.height())

        # -- Playhead handle: prominent red grab handle at the top --
        handle_rect = self._playhead_handle_rect()
        painter.setBrush(QColor(255, 60, 60))
        painter.setPen(QPen(QColor(200, 40, 40), 1))
        painter.drawRect(handle_rect)

        # Draw a small triangle/arrow indicator inside the handle
        painter.setPen(QPen(QColor(255, 200, 200), 1))
        mid_x = handle_rect.center().x()
        handle_top = handle_rect.top() + 4
        handle_bottom = handle_rect.bottom() - 4
        # Small arrow pointing down
        for offset in range(3):
            left = mid_x - 4 + offset * 3
            right = mid_x + 4 - offset * 3
            y_pos = handle_top + offset * 4
            painter.drawLine(left, y_pos, right, y_pos)

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def find_clip_at(self, x, y):
        if self.timeline is None:
            return None

        track_y = TRACK_START_Y
        for track in self.timeline.tracks:
            for clip in track.clips:
                if self._clip_rect(clip, track_y).contains(x, y):
                    return clip
            track_y += TRACK_HEIGHT + TRACK_GAP

        return None

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event: QMouseEvent):
        x, y = int(event.position().x()), int(event.position().y())

        # Playhead dragging has highest priority
        if self._dragging_playhead:
            target_frame = self._timeline_frame_at(x)
            self.playhead_dragged.emit(target_frame)
            event.accept()
            return

        # Hover detection for the playhead handle
        was_hovering = self._hovering_playhead
        self._hovering_playhead = self._playhead_hit_test(x, y) and x >= TRACK_LABEL_WIDTH
        if was_hovering != self._hovering_playhead:
            self._update_cursor()

        if self.dragging_clip is None:
            super().mouseMoveEvent(event)
            return

        timeline_frame = self._timeline_frame_at(event.position().x())

        if self.drag_mode == "move":
            frame_delta = int((event.position().x() - self.drag_start_x) / PIXELS_PER_FRAME)
            self.clip_move_requested.emit(
                self.dragging_clip,
                max(0, self.drag_start_frame + frame_delta),
            )
        else:
            self.clip_trim_requested.emit(
                self.dragging_clip,
                self.drag_mode,
                timeline_frame,
            )

        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        pos = event.position()
        x, y = int(pos.x()), int(pos.y())

        # 1. Playhead drag: highest priority - only activates on the handle
        if self._playhead_hit_test(x, y) and x >= TRACK_LABEL_WIDTH:
            self._dragging_playhead = True
            self._update_cursor()
            self.playhead_dragged.emit(self._timeline_frame_at(x))
            event.accept()
            return

        # 2. Ruler click (seek)
        if y <= RULER_HEIGHT and x >= TRACK_LABEL_WIDTH:
            self.ruler_clicked.emit(self._timeline_frame_at(x))
            event.accept()
            return

        # 3. Blade mode: split on clip click instead of selecting
        if self.blade_mode:
            clip = self.find_clip_at(x, y)
            if clip is not None:
                self.split_at_frame.emit(self._timeline_frame_at(x))
                event.accept()
                return

        # 4. Normal clip interaction (select / move / trim)
        clip = self.find_clip_at(x, y)
        if clip is None:
            # Click in empty space - seek there
            if x >= TRACK_LABEL_WIDTH:
                self.ruler_clicked.emit(self._timeline_frame_at(x))
            return super().mousePressEvent(event)

        self.selected_clip = clip
        self.clip_selected.emit(clip)

        rect = self._clip_rect(clip, TRACK_START_Y)
        if pos.x() <= rect.left() + TRIM_HANDLE_WIDTH:
            self.drag_mode = "start"
        elif pos.x() >= rect.right() - TRIM_HANDLE_WIDTH:
            self.drag_mode = "end"
        else:
            self.drag_mode = "move"

        self.dragging_clip = clip
        self.clip_edit_started.emit()
        self.drag_start_x = pos.x()
        self.drag_start_frame = clip.timeline_start_frame
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging_playhead:
                self._dragging_playhead = False
                self._update_cursor()
                event.accept()
                return
            if self.dragging_clip is not None:
                self.clip_edit_finished.emit()
            self.dragging_clip = None
            self.drag_mode = None
        super().mouseReleaseEvent(event)