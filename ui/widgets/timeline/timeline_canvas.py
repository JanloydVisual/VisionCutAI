from pathlib import Path

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QMouseEvent, QFont, QCursor, QFontMetrics
from PyQt6.QtCore import Qt, QRect, pyqtSignal


PIXELS_PER_FRAME = 2
TRACK_HEIGHT = 60
TRACK_GAP = 10
TRACK_START_Y = 40
TRACK_LABEL_WIDTH = 140
RULER_HEIGHT = 30
TRIM_HANDLE_WIDTH = 8
PLAYHEAD_HANDLE_HALF_WIDTH = 8
PLAYHEAD_HANDLE_HEIGHT = 22
FLOAT_BOX_WIDTH = 160
FLOAT_BOX_PADDING = 8


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
    blade_preview_frame = pyqtSignal(int)

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

        # Blade preview
        self._blade_preview_frame = -1  # -1 = not visible
        self._blade_mouse_y = 0

        self.setMinimumHeight(150)
        self.setMouseTracking(True)
        self._update_cursor()

    def sizeHint(self):
        """Return virtual timeline size for scroll area content."""
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        """Preferred virtual size: wide enough for scrolling, compact height."""
        from PyQt6.QtCore import QSize
        return QSize(4000, 150)

    def set_blade_mode(self, enabled: bool) -> None:
        self.blade_mode = enabled
        if not enabled:
            self._blade_preview_frame = -1
        self._update_cursor()
        self.update()

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
        phx = self._playhead_x()
        return QRect(
            phx - PLAYHEAD_HANDLE_HALF_WIDTH,
            0,
            PLAYHEAD_HANDLE_HALF_WIDTH * 2,
            PLAYHEAD_HANDLE_HEIGHT,
        )

    def _playhead_hit_test(self, x, y):
        return self._playhead_handle_rect().contains(x, y)

    # ------------------------------------------------------------------
    # Floating blade info box
    # ------------------------------------------------------------------

    def _draw_blade_info_box(self, painter, blade_x: int, preview_frame: int):
        """Draw a floating info box near the blade preview line."""
        if self.timeline is None:
            return

        clip = self.timeline.clip_at_timeline_frame(preview_frame)
        if clip is None:
            return

        # Calculate cut info
        seconds = preview_frame / self.fps if self.fps > 0 else 0
        cut_offset = preview_frame - clip.timeline_start_frame
        cut_source_frame = clip.start_frame + cut_offset
        cut_seconds = cut_source_frame / self.fps if self.fps > 0 else 0
        clip_duration = clip.frame_count / self.fps if self.fps > 0 else 0
        before_seconds = cut_offset / self.fps if self.fps > 0 else 0
        after_seconds = (clip.frame_count - cut_offset - 1) / self.fps if self.fps > 0 else 0

        # Build text lines
        lines = [
            "Cut Position",
            f"Frame: {preview_frame}",
            f"Time: {seconds:.2f}s",
            f"Before: {before_seconds:.2f}s",
            f"After:  {after_seconds:.2f}s",
        ]

        # Measure text
        info_font = QFont("monospace", 9)
        info_font.setBold(False)
        painter.setFont(info_font)
        fm = QFontMetrics(info_font)

        line_height = fm.height() + 2
        box_w = FLOAT_BOX_WIDTH
        box_h = len(lines) * line_height + FLOAT_BOX_PADDING * 2

        # Position box to the right of the blade line, or to the left if near edge
        box_x = blade_x + 12
        if box_x + box_w > self.width():
            box_x = blade_x - box_w - 12
        box_x = max(4, box_x)

        box_y = min(self._blade_mouse_y, self.height() - box_h - 4)
        box_y = max(RULER_HEIGHT + 4, box_y)

        # Draw background
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(QColor(20, 20, 20, 220))
        painter.drawRoundedRect(box_x, box_y, box_w, box_h, 4, 4)

        # Draw text
        painter.setPen(Qt.GlobalColor.white)
        text_x = box_x + FLOAT_BOX_PADDING
        text_y = box_y + FLOAT_BOX_PADDING + fm.ascent()

        for i, line in enumerate(lines):
            if i == 0:
                info_font.setBold(True)
                painter.setFont(info_font)
                painter.setPen(QColor(255, 200, 100))
            else:
                info_font.setBold(False)
                painter.setFont(info_font)
                painter.setPen(Qt.GlobalColor.white)
            painter.drawText(text_x, text_y + i * line_height, line)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def _draw_track_background(self, painter, y, track):
        painter.fillRect(
            TRACK_LABEL_WIDTH, y, self.width(), TRACK_HEIGHT, QColor(58, 58, 58)
        )
        painter.fillRect(
            0, y, TRACK_LABEL_WIDTH, TRACK_HEIGHT, QColor(43, 43, 43)
        )
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(TRACK_LABEL_WIDTH, y, TRACK_LABEL_WIDTH, y + TRACK_HEIGHT)
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

        # Note: Ruler is now drawn by TimelineRuler widget above the scroll area

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

        # -- Blade preview line (only in blade mode, follows mouse) --
        if self.blade_mode and self._blade_preview_frame >= 0:
            blade_x = TRACK_LABEL_WIDTH + self._blade_preview_frame * PIXELS_PER_FRAME
            painter.setPen(QPen(QColor(255, 255, 255, 160), 1, Qt.PenStyle.DashLine))
            painter.drawLine(blade_x, RULER_HEIGHT, blade_x, self.height())

            # Floating info box
            self._draw_blade_info_box(painter, blade_x, self._blade_preview_frame)

        # -- Playhead: thin vertical red line --
        playhead_x = self._playhead_x()
        painter.setPen(QPen(QColor(255, 60, 60), 2))
        painter.drawLine(playhead_x, PLAYHEAD_HANDLE_HEIGHT, playhead_x, self.height())

        # -- Playhead handle --
        handle_rect = self._playhead_handle_rect()
        painter.setBrush(QColor(255, 60, 60))
        painter.setPen(QPen(QColor(200, 40, 40), 1))
        painter.drawRect(handle_rect)

        painter.setPen(QPen(QColor(255, 200, 200), 1))
        mid_x = handle_rect.center().x()
        handle_top = handle_rect.top() + 4
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

        # Blade preview: update preview line AND emit preview seek signal
        if self.blade_mode and x >= TRACK_LABEL_WIDTH:
            preview_frame = self._timeline_frame_at(x)
            self._blade_mouse_y = y
            if preview_frame != self._blade_preview_frame:
                self._blade_preview_frame = preview_frame
                self.blade_preview_frame.emit(preview_frame)
                self.update()
        else:
            if self._blade_preview_frame >= 0:
                self._blade_preview_frame = -1
                self.update()

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

        # 1. Playhead drag: highest priority
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

        # 3. Blade mode: split on clip click
        if self.blade_mode:
            clip = self.find_clip_at(x, y)
            if clip is not None:
                self.split_at_frame.emit(self._timeline_frame_at(x))
                event.accept()
                return

        # 4. Normal clip interaction
        clip = self.find_clip_at(x, y)
        if clip is None:
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