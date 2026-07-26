import threading
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np

from core.ai.models import QualityGrade

@dataclass
class AnchorState:
    frame_number: int
    mask: np.ndarray
    bounding_box: Tuple[int, int, int, int]
    positive_points: List[Tuple[int, int]]
    negative_points: List[Tuple[int, int]]
    quality_grade: QualityGrade

class AnchorManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._anchors = {}

    def add_anchor(self, anchor: AnchorState):
        with self._lock:
            self._anchors[anchor.frame_number] = anchor

    def get_anchor(self, frame_number: int) -> Optional[AnchorState]:
        with self._lock:
            return self._anchors.get(frame_number)

    def get_nearest_anchor(self, frame_number: int) -> Optional[AnchorState]:
        with self._lock:
            if not self._anchors:
                return None
            
            # Find the closest anchor that is strictly before the current frame,
            # or the absolute closest if none are before.
            past_anchors = [f for f in self._anchors.keys() if f <= frame_number]
            if past_anchors:
                nearest_frame = max(past_anchors)
            else:
                nearest_frame = min(self._anchors.keys())
                
            return self._anchors[nearest_frame]

    def remove_anchor(self, frame_number: int):
        with self._lock:
            if frame_number in self._anchors:
                del self._anchors[frame_number]

    def clear(self):
        with self._lock:
            self._anchors.clear()
