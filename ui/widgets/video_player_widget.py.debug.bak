"""
VideoPlayerWidget
------------------
Composes the center editing surface:
    VideoPreview      (zoom/pan viewer + overlay + comparison)
    PlaybackControls  (Play/Pause/Stop)
    TimelineWidget    (scrub bar, step buttons, position display)

This class arranges children and re-exposes what MainWindow needs.
It holds NO business logic and never imports core/ or ai/.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap

from ui.widgets.video_preview import VideoPreview
from ui.widgets.playback_controls import PlaybackControls
from ui.widgets.timeline_widget import TimelineWidget


class VideoPlayerWidget(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    frame_scrubbed = pyqtSignal(int)
    next_frame_clicked = pyqtSignal()
    previous_frame_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.preview = VideoPreview()
        layout.addWidget(self.preview, stretch=1)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.info_label)

        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet("color: #aaa;")
        layout.addWidget(self.status_label)

        self.controls = PlaybackControls()
        self.controls.set_controls_enabled(False)
        layout.addWidget(self.controls)

        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)

        self.controls.play_clicked.connect(self.play_clicked.emit)
        self.controls.pause_clicked.connect(self.pause_clicked.emit)
        self.controls.stop_clicked.connect(self.stop_clicked.emit)

        self.timeline.frame_scrubbed.connect(self.frame_scrubbed.emit)
        self.timeline.next_frame_clicked.connect(self.next_frame_clicked.emit)
        self.timeline.previous_frame_clicked.connect(self.previous_frame_clicked.emit)

    # ---------------- Public API ----------------
    def load_frame(self, pixmap: QPixmap) -> None:
        self.preview.load_frame(pixmap)

    def set_processed_frame(self, pixmap: QPixmap) -> None:
        self.preview.set_processed_frame(pixmap)

    def clear(self) -> None:
        self.preview.clear()
        self.status_label.setText("Idle")
        self.info_label.setText("")

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_video_info(self, info: str) -> None:
        self.info_label.setText(info)

    def set_controls_enabled(self, enabled: bool) -> None:
        self.controls.set_controls_enabled(enabled)

    def set_total_frames(self, total_frames: int, fps: float) -> None:
        self.timeline.set_total_frames(total_frames, fps)

    def set_current_frame(self, frame_index: int) -> None:
        self.timeline.set_current_frame(frame_index)

    def get_overlay_widget(self):
        return self.preview.get_overlay()

    def get_timeline_widget(self) -> TimelineWidget:
        return self.timeline
