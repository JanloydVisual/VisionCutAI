import abc
import numpy as np


class IVideoDecoder(abc.ABC):
    """
    Abstract interface for video decoding backends.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Returns the name of the decoder (e.g., 'OpenCV', 'FFmpeg NVDEC')."""
        pass

    @property
    @abc.abstractmethod
    def fps(self) -> float:
        pass

    @property
    @abc.abstractmethod
    def total_frames(self) -> int:
        pass

    @property
    @abc.abstractmethod
    def width(self) -> int:
        pass

    @property
    @abc.abstractmethod
    def height(self) -> int:
        pass

    @abc.abstractmethod
    def load(self, filepath: str) -> bool:
        """
        Open the video file and initialize decoding.
        Returns True if successful, False otherwise.
        """
        pass

    @abc.abstractmethod
    def read_frame(self, frame_index: int) -> tuple[bool, np.ndarray | None]:
        """
        Read a specific frame. The engine will sequentially read current_index + 1
        during playback, or jump to a random index during seeking.
        Returns (success, frame_bgr_array).
        """
        pass

    @abc.abstractmethod
    def seek(self, frame_index: int) -> bool:
        """
        Optional hint to seek the underlying stream to a frame before reading.
        Returns True if seek was successful.
        """
        pass

    @abc.abstractmethod
    def release(self) -> None:
        """Release resources."""
        pass
