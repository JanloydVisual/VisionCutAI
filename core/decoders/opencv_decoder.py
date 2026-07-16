import cv2
import numpy as np

from .base_decoder import IVideoDecoder


class OpenCVDecoder(IVideoDecoder):
    """
    Fallback standard OpenCV decoder using CPU.
    """

    def __init__(self):
        self.cap = None
        self._fps = 30.0
        self._total_frames = 0
        self._width = 0
        self._height = 0
        self._last_frame_index = -1

    @property
    def name(self) -> str:
        return "OpenCV (CPU)"

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def load(self, filepath: str) -> bool:
        self.release()
        self.cap = cv2.VideoCapture(filepath)
        if not self.cap.isOpened():
            return False

        self._fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self._fps <= 1:
            self._fps = 30.0
            
        self._total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._last_frame_index = -1
        return True

    def read_frame(self, frame_index: int) -> tuple[bool, np.ndarray | None]:
        if not self.cap:
            return False, None
            
        # If the requested frame is not the immediate next one, seek first
        if frame_index != self._last_frame_index + 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            
        success, frame = self.cap.read()
        if success:
            self._last_frame_index = frame_index
            return True, frame
        return False, None

    def seek(self, frame_index: int) -> bool:
        if not self.cap:
            return False
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        self._last_frame_index = frame_index - 1
        return True

    def release(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None
