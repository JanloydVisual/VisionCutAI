from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QAbstractScrollArea,
    QPushButton,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal

from ui.widgets.timeline.timeline_canvas import (
    TimelineCanvas,
    TRACK_LABEL_WIDTH,
    PIXELS_PER_FRAME,
)
from ui.widgets.timeline.timeline_ruler import TimelineRuler
from ui.widgets.timeline.track_header import TrackHeaderColumn


class TimelineEditor(QWidget):
    seek_requested = pyqtSignal(int)
    split_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    clip_selected = pyqtSignal(object)
    clip_move_requested = pyqtSignal(object, int)
    clip_trim_requested = pyqtSignal(object, str, int)
    clip_edit_started = pyqtSignal()
    clip_edit_finished = pyqtSignal()
    split_at_frame = pyqtSignal(int)
    playhead_dragged = pyqtSignal(int)
    blade_preview_frame = pyqtSignal(int)

    AUTO_SCROLL_MARGIN = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        toolbar = QHBoxLayout()
        self.split_button = QPushButton("Split at Playhead")
        self.delete_button = QPushButton("Delete Selected")
        toolbar.addWidget(self.split_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addWidget(QLabel("Drag clips to move - drag yellow edges to trim"))
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        # Ruler row: a spacer matches the header column width so the
        # ruler's time markings line up with the scrollable canvas,
        # not the fixed header.
        ruler_row = QHBoxLayout()
        ruler_row.setContentsMargins(0, 0, 0, 0)
        ruler_row.setSpacing(0)
        ruler_spacer = QWidget()
        ruler_spacer.setFixedWidth(TRACK_LABEL_WIDTH)
        self.ruler = TimelineRuler()
        ruler_row.addWidget(ruler_spacer)
        ruler_row.addWidget(self.ruler)
        root.addLayout(ruler_row)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.header = TrackHeaderColumn()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setMinimumWidth(200)
        self.scroll.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)

        self.canvas = TimelineCanvas()
        self.scroll.setWidget(self.canvas)

        body.addWidget(self.header)
        body.addWidget(self.scroll)
        root.addLayout(body)

        self.scroll.horizontalScrollBar().valueChanged.connect(
            self.ruler.set_scroll_offset
        )

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(90)

        self.split_button.clicked.connect(self.split_requested.emit)
        self.delete_button.clicked.connect(self.delete_requested.emit)

        self.canvas.ruler_clicked.connect(self.seek_requested.emit)
        self.canvas.clip_selected.connect(self.clip_selected.emit)
        self.canvas.clip_move_requested.connect(self.clip_move_requested.emit)
        self.canvas.clip_trim_requested.connect(self.clip_trim_requested.emit)
        self.canvas.clip_edit_started.connect(self.clip_edit_started.emit)
        self.canvas.clip_edit_finished.connect(self.clip_edit_finished.emit)
        self.canvas.split_at_frame.connect(self.split_at_frame.emit)
        self.canvas.playhead_dragged.connect(self.playhead_dragged.emit)
        self.canvas.blade_preview_frame.connect(self.blade_preview_frame.emit)

    def set_project(self, project):
        self.project = project
        if project:
            self.canvas.set_timeline(project.timeline)
            self.header.set_timeline(project.timeline)

    def set_fps(self, fps):
        self.canvas.set_fps(fps)
        self.ruler.set_fps(fps)

    def refresh(self):
        self.canvas.refresh()
        self.header.update()

    def set_blade_mode(self, enabled: bool) -> None:
        self.canvas.set_blade_mode(enabled)

    def set_playhead_frame(self, frame_index):
        self.canvas.set_playhead_frame(frame_index)
        self._auto_scroll_to_playhead(frame_index)

    def _auto_scroll_to_playhead(self, frame_index):
        playhead_x = TRACK_LABEL_WIDTH + (frame_index * PIXELS_PER_FRAME)

        bar = self.scroll.horizontalScrollBar()
        viewport_width = self.scroll.viewport().width()
        visible_left = bar.value()
        visible_right = visible_left + viewport_width

        if playhead_x < visible_left + self.AUTO_SCROLL_MARGIN:
            bar.setValue(max(0, playhead_x - self.AUTO_SCROLL_MARGIN))
        elif playhead_x > visible_right - self.AUTO_SCROLL_MARGIN:
            bar.setValue(playhead_x - viewport_width + self.AUTO_SCROLL_MARGIN)
