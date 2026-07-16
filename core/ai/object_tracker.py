import cv2
import numpy as np
from typing import Tuple, Optional

class ObjectTracker:
    """
    A unified wrapper for OpenCV trackers.
    Initializes with a specific tracker (MIL by default) and tracks an object across frames.
    """

    def __init__(self):
        self.tracker = None
        self.bbox: Optional[Tuple[int, int, int, int]] = None
        self.is_tracking = False
        self.prompt_type = 'rectangle'
        self.label = 1

    def init_tracker(self, frame: np.ndarray, prompt: dict):
        """
        Initialize the tracker with a starting frame and prompt dictionary.
        """
        try:
            self.prompt_type = prompt.get('type', 'rectangle')
            self.label = prompt.get('label', 1)
            
            if self.prompt_type == 'point':
                px, py = prompt['data']
                bbox = (px - 20, py - 20, 40, 40)
            else:
                bbox = prompt['data']
                
            h, w = frame.shape[:2]
            x, y, bw, bh = bbox
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            bw = max(1, min(bw, w - x))
            bh = max(1, min(bh, h - y))
            clamped_bbox = (x, y, bw, bh)

            # Create a fresh tracker instance
            self.tracker = cv2.TrackerMIL_create()
            self.tracker.init(frame, clamped_bbox)
            self.bbox = clamped_bbox
            self.is_tracking = True
        except Exception as e:
            print(f"Failed to initialize tracker: {e}")
            self.is_tracking = False

    def update(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Update the tracker with the next frame.
        Returns the new bounding box (x, y, w, h) if tracking is successful, None otherwise.
        """
        if not self.is_tracking or self.tracker is None:
            return None

        success, bbox = self.tracker.update(frame)
        if success:
            self.bbox = tuple(map(int, bbox))
            return self.bbox
        else:
            self.is_tracking = False
            self.bbox = None
            return None

    def reset(self):
        """Reset the tracker."""
        self.tracker = None
        self.bbox = None
        self.is_tracking = False

    def get_bbox(self) -> Optional[Tuple[int, int, int, int]]:
        return self.bbox

    def get_sam_prompt(self) -> Optional[list]:
        """
        Convert the current bounding box to a prompt format suitable for rembg (SAM mode).
        rembg SAM mode expects a prompt list, where each prompt is a dict.
        For a bounding box:
        {'type': 'rectangle', 'data': [x1, y1, x2, y2], 'label': 1}
        """
        if not self.is_tracking or self.bbox is None:
            return None

        x, y, w, h = self.bbox
        if self.prompt_type == 'point':
            # Use the center of the tracked box
            cx = x + w // 2
            cy = y + h // 2
            return [{'type': 'point', 'data': [cx, cy], 'label': self.label}]
        else:
            return [{'type': 'rectangle', 'data': [x, y, x + w, y + h], 'label': self.label}]
