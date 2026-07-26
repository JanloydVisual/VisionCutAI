import cv2
import numpy as np
from typing import Tuple, Optional
from core.ai.trackers.base_tracker import BaseTracker

class OpenCVTrackerWrapper(BaseTracker):
    def __init__(self, create_fn, name):
        super().__init__()
        self.create_fn = create_fn
        self.name = name
        self.tracker = None

    def init(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
        try:
            self.tracker = self.create_fn()
            success = self.tracker.init(frame, tuple(map(int, bbox)))
            
            # OpenCV init() may return None in some python bindings
            if success is None or success:
                self.is_tracking = True
                return True
            return False
        except Exception as e:
            print(f"Failed to initialize {self.name} Tracker: {e}")
            self.is_tracking = False
            return False

    def update(self, frame: np.ndarray) -> Tuple[bool, Optional[Tuple[int, int, int, int]], float]:
        if not self.is_tracking or self.tracker is None:
            return False, None, 0.0
        
        ok, bbox = self.tracker.update(frame)
        if ok:
            return True, bbox, 1.0
        else:
            self.is_tracking = False
            return False, None, 0.0

    def reset(self):
        super().reset()
        self.tracker = None


class TrackerFactory:
    @staticmethod
    def create_tracker() -> Tuple[BaseTracker, str]:
        """
        Creates and returns the best available OpenCV tracker and its name.
        Selection priority: 1. CSRT, 2. KCF, 3. MIL
        """
        if hasattr(cv2, 'TrackerCSRT_create'):
            return OpenCVTrackerWrapper(cv2.TrackerCSRT_create, "CSRT"), "CSRT"
        elif hasattr(cv2, 'TrackerKCF_create'):
            return OpenCVTrackerWrapper(cv2.TrackerKCF_create, "KCF"), "KCF"
        elif hasattr(cv2, 'TrackerMIL_create'):
            return OpenCVTrackerWrapper(cv2.TrackerMIL_create, "MIL"), "MIL"
        else:
            raise RuntimeError("No supported OpenCV trackers found.")
