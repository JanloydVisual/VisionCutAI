from pathlib import Path

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QMouseEvent
from PyQt6.QtCore import Qt, QRect, pyqtSignal


PIXELS_PER_FRAME = 2
TRACK_HEIGHT = 60
TRACK_GAP = 10
TRACK_START_Y = 40
TRACK_LABEL_WIDTH = 140
RULER_HEIGHT = 30


class TimelineCanvas(QWidget):

    ruler_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.timeline = None
        self.playhead_frame = 0
        self.fps = 30.0

        self.selected_clip = None

        self.setMinimumSize(4000, 300)

    def set_timeline(self, timeline):

        self.timeline = timeline
        self.update()

    def set_fps(self, fps: float):

        self.fps = fps if fps and fps > 0 else 30.0
        self.update()

    def set_playhead_frame(self, frame):

        self.playhead_frame = max(0, frame)
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            QColor(36,36,36)
        )

        # ruler

        painter.fillRect(
            0,
            0,
            self.width(),
            RULER_HEIGHT,
            QColor(48,48,48)
        )

        painter.setPen(
            QPen(QColor(110,110,110))
        )

        for x in range(TRACK_LABEL_WIDTH, self.width(), 100):

            painter.drawLine(
                x,
                0,
                x,
                RULER_HEIGHT
            )

            frame = (
                x - TRACK_LABEL_WIDTH
            ) / PIXELS_PER_FRAME

            second = int(frame / self.fps)

            painter.drawText(
                x + 4,
                20,
                f"{second:02}"
            )


        if self.timeline is None:
            return


        y = TRACK_START_Y


        for track in self.timeline.tracks:

            painter.fillRect(
                TRACK_LABEL_WIDTH,
                y,
                self.width(),
                TRACK_HEIGHT,
                QColor(58,58,58)
            )

            painter.setPen(
                Qt.GlobalColor.white
            )

            painter.drawText(
                10,
                y + 35,
                track.name
            )


            x = TRACK_LABEL_WIDTH


            for clip in track.clips:

                width = max(
                    120,
                    clip.frame_count * PIXELS_PER_FRAME
                )

                rect = QRect(
                    x,
                    y + 8,
                    width,
                    44
                )


                painter.fillRect(
                    rect,
                    QColor(70,120,220)
                )


                if clip == self.selected_clip:

                    painter.setPen(
                        QPen(
                            QColor(255,215,0),
                            3
                        )
                    )

                else:

                    painter.setPen(
                        Qt.GlobalColor.white
                    )


                painter.drawRect(rect)


                painter.drawText(
                    rect.adjusted(10,0,-10,0),
                    Qt.AlignmentFlag.AlignVCenter,
                    Path(clip.source_path).name
                )


                x += width + 8


            y += TRACK_HEIGHT + TRACK_GAP


        # playhead

        playhead_x = (
            TRACK_LABEL_WIDTH +
            self.playhead_frame * PIXELS_PER_FRAME
        )


        painter.setPen(
            QPen(
                QColor(255,60,60),
                2
            )
        )

        painter.drawLine(
            playhead_x,
            0,
            playhead_x,
            self.height()
        )


    def mousePressEvent(self, event: QMouseEvent):

        if event.button() == Qt.MouseButton.LeftButton:

            pos = event.position()


            # ruler click

            if (
                pos.y() <= RULER_HEIGHT
                and pos.x() >= TRACK_LABEL_WIDTH
            ):

                frame = int(
                    (
                        pos.x()
                        -
                        TRACK_LABEL_WIDTH
                    )
                    /
                    PIXELS_PER_FRAME
                )

                self.ruler_clicked.emit(
                    max(0, frame)
                )

                event.accept()
                return


            # clip selection

            if self.timeline:

                y = TRACK_START_Y


                for track in self.timeline.tracks:

                    x = TRACK_LABEL_WIDTH


                    for clip in track.clips:

                        width = max(
                            120,
                            clip.frame_count * PIXELS_PER_FRAME
                        )


                        rect = QRect(
                            x,
                            y + 8,
                            width,
                            44
                        )


                        if rect.contains(
                            int(pos.x()),
                            int(pos.y())
                        ):

                            self.selected_clip = clip

                            self.timeline.select_clip(
                                clip
                            )

                            self.update()

                            event.accept()
                            return


                        x += width + 8


                    y += TRACK_HEIGHT + TRACK_GAP


        super().mousePressEvent(event)
