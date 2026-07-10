import cv2
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class VideoEngine(QObject):
    """
    Handles video playback.

    Responsibilities:
    - Load video
    - Play
    - Pause
    - Stop
    - Step forward / backward by one frame
    - Seek to an arbitrary frame (timeline scrubbing)
    - Emit frames to the GUI

    Does NOT know anything about buttons,
    windows or labels.
    """

    frame_ready = pyqtSignal(object)
    video_loaded = pyqtSignal(dict)
    playback_finished = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.cap = None

        self.timer = QTimer()
        self.timer.timeout.connect(self._next_frame)

        self.is_loaded = False
        self.is_playing = False

        self.fps = 30
        self.total_frames = 0

        # Tracks the index of the frame currently on screen.
        self.current_frame_index = 0

    def load_video(self, filepath):

        if self.cap:
            self.pause()
            self.cap.release()

        self.cap = cv2.VideoCapture(filepath)

        if not self.cap.isOpened():
            return False

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        if self.fps <= 1:
            self.fps = 30

        self.total_frames = int(
            self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        self.timer.setInterval(
            int(1000 / self.fps)
        )

        self.is_loaded = True

        info = {
            "Width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "Height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "FPS": self.fps,
            "Frames": self.total_frames,
        }

        self.video_loaded.emit(info)

        self._seek_and_show(0)

        return True

    def play(self):

        if not self.is_loaded:
            return

        self.is_playing = True
        self.timer.start()

    def pause(self):

        self.is_playing = False
        self.timer.stop()

    def stop(self):

        if not self.is_loaded:
            return

        self.pause()
        self._seek_and_show(0)

    def next_frame(self):

        if not self.is_loaded:
            return

        self.pause()

        target = self.current_frame_index + 1

        if target > self.total_frames - 1:
            target = self.total_frames - 1

        self._seek_and_show(target)

    def previous_frame(self):

        if not self.is_loaded:
            return

        self.pause()

        target = self.current_frame_index - 1

        if target < 0:
            target = 0

        self._seek_and_show(target)

    def seek(self, frame_index):
        """
        Seeks to an arbitrary frame position (used by timeline
        scrubbing). Pauses playback first and clamps to valid
        bounds, same defensive pattern as next_frame/previous_frame.
        """

        if not self.is_loaded:
            return

        self.pause()

        target = frame_index

        if target < 0:
            target = 0
        elif target > self.total_frames - 1:
            target = self.total_frames - 1

        self._seek_and_show(target)

    def _seek_and_show(self, frame_index):

        if not self.cap:
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        success, frame = self.cap.read()

        if success:
            self.current_frame_index = frame_index
            self.frame_ready.emit(frame)

    def _next_frame(self):

        if not self.cap:
            return

        success, frame = self.cap.read()

        if not success:

            self.stop()

            self.playback_finished.emit()

            return

        self.current_frame_index += 1
        self.frame_ready.emit(frame)

    def release(self):

        self.pause()

        if self.cap:
            self.cap.release()
            self.cap = None

        self.is_loaded = False
        self.is_playing = False
