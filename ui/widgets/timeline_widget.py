"""
TimelineWidget
--------------
Real scrubbing timeline: slider, Previous/Next frame buttons,
frame counter, and timecode display.

Emits:
    frame_scrubbed(int)      - live, fired while the user drags
    next_frame_clicked()
    previous_frame_clicked()

Has NO knowledge of VideoEngine or Controller - purely UI,
same as every other widget in this package.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QPushButton,
    QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal


class TimelineWidget(QWidget):

    frame_scrubbed = pyqtSignal(int)
    next_frame_clicked = pyqtSignal()
    previous_frame_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.total_frames = 0
        self.fps = 30.0

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(4)

        # ---------------- Slider row ----------------
        slider_row = QHBoxLayout()

        self.previous_button = QPushButton("\u25c0")
        self.previous_button.setFixedWidth(32)
        self.previous_button.setToolTip("Previous Frame")

        self.next_button = QPushButton("\u25b6")
        self.next_button.setFixedWidth(32)
        self.next_button.setToolTip("Next Frame")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.setValue(0)

        slider_row.addWidget(self.previous_button)
        slider_row.addWidget(self.slider, stretch=1)
        slider_row.addWidget(self.next_button)

        root.addLayout(slider_row)

        # ---------------- Info row ----------------
        info_row = QHBoxLayout()

        self.timecode_label = QLabel("00:00:00:00")
        self.timecode_label.setStyleSheet("color: #aaa; font-size: 11px;")

        self.frame_counter_label = QLabel("0 / 0")
        self.frame_counter_label.setStyleSheet("color: #aaa; font-size: 11px;")

        info_row.addWidget(self.timecode_label)
        info_row.addStretch(1)
        info_row.addWidget(self.frame_counter_label)

        root.addLayout(info_row)

        self.setStyleSheet(
            "background-color: #1e1e1e; border: 1px solid #333;"
        )

        # sliderMoved fires only on user drag, never on programmatic
        # setValue(). This is what prevents feedback loops when the
        # slider position is updated from live playback.
        self.slider.sliderMoved.connect(self.frame_scrubbed.emit)
        self.previous_button.clicked.connect(self.previous_frame_clicked.emit)
        self.next_button.clicked.connect(self.next_frame_clicked.emit)

    def set_total_frames(self, total_frames: int, fps: float) -> None:
        self.total_frames = max(total_frames - 1, 0)
        self.fps = fps if fps and fps > 0 else 30.0

        self.slider.setMinimum(0)
        self.slider.setMaximum(self.total_frames)

        self.set_current_frame(0)

    def set_current_frame(self, frame_index: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(frame_index)
        self.slider.blockSignals(False)

        self.frame_counter_label.setText(
            f"{frame_index} / {self.total_frames}"
        )
        self.timecode_label.setText(self._to_timecode(frame_index))

    def _to_timecode(self, frame_index: int) -> str:
        total_seconds = frame_index / self.fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frames = int(frame_index % round(self.fps))
        return f"{hours:02}:{minutes:02}:{seconds:02}:{frames:02}"
