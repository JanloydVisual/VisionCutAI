from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
)
from PyQt6.QtCore import pyqtSignal

from ui.widgets.timeline.timeline_canvas import (
    TimelineCanvas,
    TRACK_LABEL_WIDTH,
    PIXELS_PER_FRAME,
)
from ui.widgets.timeline.track_header import TrackHeader


class TimelineEditor(QWidget):

    seek_requested = pyqtSignal(int)

    AUTO_SCROLL_MARGIN = 40

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.header = TrackHeader("Video Track 1")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)

        self.canvas = TimelineCanvas()
        self.scroll.setWidget(self.canvas)

        body.addWidget(self.header)
        body.addWidget(self.scroll)

        root.addLayout(body)

        self.setMinimumHeight(220)

        self.canvas.ruler_clicked.connect(self.seek_requested.emit)

    def set_project(self, project):

        self.project = project

        if project:
            self.canvas.set_timeline(project.timeline)

    def set_fps(self, fps: float) -> None:
        self.canvas.set_fps(fps)

    def refresh(self) -> None:
        self.canvas.update()

    def set_playhead_frame(self, frame_index: int) -> None:
        self.canvas.set_playhead_frame(frame_index)
        self._auto_scroll_to_playhead(frame_index)

    def _auto_scroll_to_playhead(self, frame_index: int) -> None:
        """
        Keeps the playhead visible during playback/scrubbing. Only
        scrolls when the playhead is about to leave the visible
        viewport (with a margin) - not every frame - so it doesn't
        fight a user who scrolled elsewhere on purpose.
        """
        playhead_x = TRACK_LABEL_WIDTH + (frame_index * PIXELS_PER_FRAME)

        bar = self.scroll.horizontalScrollBar()
        viewport_width = self.scroll.viewport().width()
        visible_left = bar.value()
        visible_right = visible_left + viewport_width

        margin = self.AUTO_SCROLL_MARGIN

        if playhead_x < visible_left + margin:
            bar.setValue(max(0, playhead_x - margin))
        elif playhead_x > visible_right - margin:
            bar.setValue(playhead_x - viewport_width + margin)
