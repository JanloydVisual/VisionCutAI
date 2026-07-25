import cv2
import numpy as np
from typing import Tuple, Optional
from .base_tracker import BaseTracker

class CSRTTracker(BaseTracker):
    """
    OpenCV CSRT Tracker implementation.
    CSRT provides high accuracy for bounding box tracking.
    """
    def __init__(self):
        super().__init__()
        self.tracker = None

    def init(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
        try:
            if hasattr(cv2, 'TrackerCSRT_create'):
                self.tracker = cv2.TrackerCSRT_create()
            else:
                print("CSRT Tracker not available. Falling back to MIL Tracker.")
                self.tracker = cv2.TrackerMIL_create()
            success = self.tracker.init(frame, bbox)
            print(f"MIL Tracker init success: {success} for bbox {bbox} on frame {frame.shape}")
            if success is None or success:
                self.is_tracking = True
                self.bbox = bbox
                self.confidence = 1.0
                return True
            return False
        except Exception as e:
            print(f"Failed to initialize CSRT Tracker: {e}")
            self.is_tracking = False
            return False

    def update(self, frame: np.ndarray) -> Tuple[bool, Optional[Tuple[int, int, int, int]], float]:
        if not self.is_tracking or self.tracker is None:
            return False, None, 0.0

        success, bbox = self.tracker.update(frame)
        if success:
            self.bbox = tuple(map(int, bbox))
            self.confidence = 1.0 # OpenCV standard trackers don't expose float confidence in python bindings easily
            return True, self.bbox, self.confidence
        else:
            self.is_tracking = False
            self.bbox = None
            self.confidence = 0.0
            return False, None, 0.0

    def reset(self):
        super().reset()
        self.tracker = None
