import cv2
import numpy as np
from typing import Tuple, Optional
from abc import ABC, abstractmethod

class BaseTracker(ABC):
    """
    Abstract base class for all object trackers in the pipeline.
    """
    def __init__(self):
        self.is_tracking = False
        self.bbox: Optional[Tuple[int, int, int, int]] = None
        self.confidence: float = 0.0

    @abstractmethod
    def init(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
        """
        Initialize the tracker with a starting frame and bounding box (x, y, w, h).
        Returns True if initialization was successful.
        """
        pass

    @abstractmethod
    def update(self, frame: np.ndarray) -> Tuple[bool, Optional[Tuple[int, int, int, int]], float]:
        """
        Update the tracker with the next frame.
        Returns:
            success (bool): Whether tracking was successful
            bbox (tuple): New bounding box (x, y, w, h) or None
            confidence (float): Confidence score (0.0 to 1.0)
        """
        pass

    def reset(self):
        """Reset the tracker state."""
        self.is_tracking = False
        self.bbox = None
        self.confidence = 0.0
