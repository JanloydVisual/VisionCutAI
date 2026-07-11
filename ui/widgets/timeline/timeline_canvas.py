from pathlib import Path

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QMouseEvent, QFont
from PyQt6.QtCore import Qt, QRect, pyqtSignal


PIXELS_PER_FRAME = 2
TRACK_HEIGHT = 60
TRACK_GAP = 10
TRACK_START_Y = 40
TRACK_LABEL_WIDTH = 140
RULER_HEIGHT = 30
TRIM_HANDLE_WIDTH = 8


class TimelineCanvas(QWidget):
    ruler_clicked = pyqtSignal(int)
    clip_selected = pyqtSignal(object)
    clip_move_requested = pyqtSignal(object, int)
    clip_trim_requested = pyqtSignal(object, str, int)
    clip_edit_started = pyqtSignal()
    clip_edit_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.timeline = None
        self.playhead_frame = 0
        self.fps = 30.0
        self.selected_clip = None

        self.dragging_clip = None
        self.drag_mode = None
        self.drag_start_x = 0
        self.drag_start_frame = 0

        self.setMinimumSize(4000, 300)

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

    @staticmethod
    def _clip_rect(clip, track_y):
        x = TRACK_LABEL_WIDTH + clip.timeline_start_frame * PIXELS_PER_FRAME
        width = max(2, clip.frame_count * PIXELS_PER_FRAME)
        return QRect(int(x), track_y + 8, int(width), 44)

    def _timeline_frame_at(self, x):
        return max(0, int((x - TRACK_LABEL_WIDTH) / PIXELS_PER_FRAME))

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
        # Ruler label area (left margin)
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

        # -- Playhead line --
        playhead_x = TRACK_LABEL_WIDTH + self.playhead_frame * PIXELS_PER_FRAME
        painter.setPen(QPen(QColor(255, 60, 60), 2))
        painter.drawLine(playhead_x, 0, playhead_x, self.height())

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

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        pos = event.position()

        if pos.y() <= RULER_HEIGHT and pos.x() >= TRACK_LABEL_WIDTH:
            self.ruler_clicked.emit(self._timeline_frame_at(pos.x()))
            event.accept()
            return

        clip = self.find_clip_at(int(pos.x()), int(pos.y()))
        if clip is None:
            return super().mousePressEvent(event)

        self.selected_clip = clip
        self.clip_selected.emit(clip)

        rect = self._clip_rect(clip, TRACK_START_Y)
        # Use the x position only: trim edge behavior does not depend on track.
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

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging_clip is None:
            return super().mouseMoveEvent(event)

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

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging_clip is not None:
                self.clip_edit_finished.emit()
            self.dragging_clip = None
            self.drag_mode = None
        super().mouseReleaseEvent(event)