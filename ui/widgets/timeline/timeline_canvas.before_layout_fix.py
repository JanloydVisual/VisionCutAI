from pathlib import Path

from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtGui import QPainter, QColor, QPen, QMouseEvent, QFont, QCursor, QFontMetrics
from PyQt6.QtCore import Qt, QRect, QTimer, pyqtSignal


PIXELS_PER_FRAME = 2
TRACK_HEIGHT = 60
TRACK_GAP = 10
TRACK_START_Y = 40
TRACK_LABEL_WIDTH = 140
RULER_HEIGHT = 30
TRIM_HANDLE_WIDTH = 8
PLAYHEAD_HANDLE_HALF_WIDTH = 8
PLAYHEAD_HANDLE_HEIGHT = 22
HOVER_TOOLTIP_DELAY_MS = 500
SNAP_DISTANCE = 5


class TimelineCanvas(QWidget):
    ruler_clicked = pyqtSignal(int)
    clip_selected = pyqtSignal(object)
    clip_move_requested = pyqtSignal(object, int)
    clip_trim_requested = pyqtSignal(object, str, int)
    clip_edit_started = pyqtSignal()
    clip_edit_finished = pyqtSignal()
    split_at_frame = pyqtSignal(int)
    playhead_dragged = pyqtSignal(int)
    blade_preview_frame = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.timeline = None
        self.playhead_frame = 0
        self._scroll_offset = 0
        self.fps = 30.0
        self.selected_clip = None
        self.blade_mode = False

        self.dragging_clip = None
        self.drag_mode = None
        self.drag_start_x = 0
        self.drag_start_frame = 0

        self._snap_indicator_frame = -1

        self._dragging_playhead = False
        self._hovering_playhead = False

        self._blade_preview_frame = -1
        self._blade_mouse_y = 0

        self._hover_clip = None
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._show_hover_tooltip)

        self.setMinimumHeight(150)
        self.setMouseTracking(True)
        self._update_cursor()

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(4000, 150)

    def minimumSizeHint(self):
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

    def set_scroll_offset(self, offset: int):
        self._scroll_offset = offset
        self.update()

    def set_playhead_frame(self, frame):
        self.playhead_frame = max(0, frame)
        self.update()

    @staticmethod
    def _clip_rect(clip, track_y):
        x = clip.timeline_start_frame * PIXELS_PER_FRAME
        width = max(2, clip.frame_count * PIXELS_PER_FRAME)
        return QRect(int(x), track_y + 8, int(width), 44)

    def _timeline_frame_at(self, x):
        return max(0, int(x / PIXELS_PER_FRAME))

    def _playhead_x(self):
        return self.playhead_frame * PIXELS_PER_FRAME

    def _playhead_handle_rect(self):
        phx = self._playhead_x()
        return QRect(
            phx - PLAYHEAD_HANDLE_HALF_WIDTH,
            -8,
            PLAYHEAD_HANDLE_HALF_WIDTH * 2,
            PLAYHEAD_HANDLE_HEIGHT + 8,
        )

    def _playhead_hit_test(self, x, y):
        return self._playhead_handle_rect().contains(x, y)

    def _draw_blade_time_label(self, painter, blade_x: int, preview_frame: int):
        if self.timeline is None:
            return

        clip = self.timeline.clip_at_timeline_frame(preview_frame)
        if clip is None:
            return

        seconds = preview_frame / self.fps if self.fps > 0 else 0
        text = f"{seconds:.2f}s"

        label_font = QFont("monospace", 9)
        label_font.setBold(True)
        painter.setFont(label_font)
        fm = QFontMetrics(label_font)
        text_w = fm.horizontalAdvance(text)

        text_x = blade_x + 8
        if text_x + text_w > self.width():
            text_x = blade_x - text_w - 8
        text_x = max(4, text_x)

        text_y = min(self._blade_mouse_y, self.height() - 4)
        text_y = max(RULER_HEIGHT + fm.ascent() + 4, text_y)

        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(text_x, text_y, text)

    def _draw_track_background(self, painter, y, track):
        # Label column (0..TRACK_LABEL_WIDTH) is drawn by the fixed
        # TrackHeaderColumn widget now, not here - this only fills
        # the scrollable content area.
        painter.fillRect(
            TRACK_LABEL_WIDTH, y, self.width(), TRACK_HEIGHT, QColor(58, 58, 58)
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(36, 36, 36))

        if self.timeline is None:
            return

        y = TRACK_START_Y
        for track in self.timeline.tracks:
            self._draw_track_background(painter, y, track)

            for clip in track.clips:
                rect = self._clip_rect(clip, y)

                if track.track_type == "audio":
                    painter.fillRect(
                        rect,
                        QColor(80, 160, 110)
                    )
                else:
                    painter.fillRect(
                        rect,
                        QColor(70, 120, 220)
                    )

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

        if self.blade_mode and self._blade_preview_frame >= 0:
            blade_x = self._blade_preview_frame * PIXELS_PER_FRAME
            painter.setPen(QPen(QColor(255, 255, 255, 160), 1, Qt.PenStyle.DashLine))
            painter.drawLine(blade_x, RULER_HEIGHT, blade_x, self.height())

            self._draw_blade_time_label(painter, blade_x, self._blade_preview_frame)

        if self._snap_indicator_frame >= 0:
            snap_x = self._snap_indicator_frame * PIXELS_PER_FRAME
            painter.setPen(QPen(QColor(0, 255, 255), 2))
            painter.drawLine(
                snap_x,
                RULER_HEIGHT,
                snap_x,
                self.height(),
            )

        playhead_x = self._playhead_x()
        painter.setPen(QPen(QColor(255, 60, 60), 2))
        painter.drawLine(playhead_x, PLAYHEAD_HANDLE_HEIGHT, playhead_x, self.height())

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

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.2f}s"
        minutes = int(seconds // 60)
        remaining = seconds % 60
        return f"{minutes}m {remaining:.1f}s"

    def _update_hover_tooltip(self, x, y) -> None:
        if self.blade_mode or self._dragging_playhead:
            return

        clip = self.find_clip_at(x, y)

        if clip is not self._hover_clip:
            QToolTip.hideText()
            self._hover_timer.stop()
            self._hover_clip = clip

            if clip is not None:
                self._hover_timer.start(HOVER_TOOLTIP_DELAY_MS)

    def _show_hover_tooltip(self) -> None:
        if self._hover_clip is None:
            return

        duration = self._hover_clip.frame_count / self.fps if self.fps > 0 else 0
        QToolTip.showText(QCursor.pos(), self._format_duration(duration), self)

    def leaveEvent(self, event):
        QToolTip.hideText()
        self._hover_timer.stop()
        self._hover_clip = None
        super().leaveEvent(event)


    def _snap_frame(self, frame, moving_clip):
        """Find the nearest snap point for clip movement."""
        targets = [0, self.playhead_frame]

        if self.timeline is not None:
            for track in self.timeline.tracks:
                for clip in track.clips:
                    if clip is moving_clip:
                        continue

                    targets.append(clip.timeline_start_frame)
                    targets.append(
                        clip.timeline_start_frame + clip.frame_count
                    )

        best_frame = frame
        best_distance = SNAP_DISTANCE + 1

        for target in targets:
            distance = abs(frame - target)

            if distance <= SNAP_DISTANCE and distance < best_distance:
                best_frame = target
                best_distance = distance

        self._snap_indicator_frame = best_frame if best_frame != frame else -1
        return best_frame

    def mouseMoveEvent(self, event: QMouseEvent):
        x, y = int(event.position().x()), int(event.position().y())

        if self._dragging_playhead:
            target_frame = self._timeline_frame_at(x)
            self.playhead_dragged.emit(target_frame)
            event.accept()
            return

        if self.blade_mode:
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

        was_hovering = self._hovering_playhead
        self._hovering_playhead = self._playhead_hit_test(x, y)
        if was_hovering != self._hovering_playhead:
            self._update_cursor()

        if self.dragging_clip is None:
            self._update_hover_tooltip(x, y)
            super().mouseMoveEvent(event)
            return

        timeline_frame = self._timeline_frame_at(event.position().x())

        if self.drag_mode == "move":
            frame_delta = int((event.position().x() - self.drag_start_x) / PIXELS_PER_FRAME)
            new_frame = max(0, self.drag_start_frame + frame_delta)
            new_frame = self._snap_frame(new_frame, self.dragging_clip)

            self.clip_move_requested.emit(
                self.dragging_clip,
                new_frame,
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

        if self._playhead_hit_test(x, y):
            self._dragging_playhead = True
            self._update_cursor()
            self.playhead_dragged.emit(self._timeline_frame_at(x))
            event.accept()
            return

        if y <= RULER_HEIGHT:
            self.ruler_clicked.emit(self._timeline_frame_at(x))
            event.accept()
            return

        if self.blade_mode:
            clip = self.find_clip_at(x, y)
            if clip is not None:
                self.split_at_frame.emit(self._timeline_frame_at(x))
                event.accept()
                return

        clip = self.find_clip_at(x, y)
        if clip is None:
            if True:
                self.ruler_clicked.emit(self._timeline_frame_at(x))
            return super().mousePressEvent(event)

        QToolTip.hideText()
        self._hover_timer.stop()
        self._hover_clip = None

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
