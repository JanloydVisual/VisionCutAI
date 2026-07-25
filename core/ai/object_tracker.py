import cv2
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass
from core.ai.trackers.csrt_tracker import CSRTTracker
from core.ai.trackers.base_tracker import BaseTracker

@dataclass
class TrackedFrameState:
    frame_number: int
    bounding_box: Tuple[int, int, int, int]
    positive_points: List[Tuple[int, int]]
    negative_points: List[Tuple[int, int]]
    confidence: float

class ObjectTracker:
    """
    A unified wrapper for abstract trackers (CSRT by default).
    Internally scales high-resolution frames down to prevent RAM explosion (OOM crashes).
    """

    def __init__(self):
        self.tracker: Optional[BaseTracker] = None
        self.state: Optional[TrackedFrameState] = None
        self.is_tracking = False
        self.label = 1
        self.scale_factor = 1.0

        # Store initial points to carry forward (as requested by Option B default or Option A future)
        self.positive_points: List[Tuple[int, int]] = []
        self.negative_points: List[Tuple[int, int]] = []
        
        self._rel_pos_points: List[Tuple[float, float]] = []
        self._rel_neg_points: List[Tuple[float, float]] = []

    def _get_scale(self, frame_shape):
        """Calculate scale factor to keep max dimension <= 640 for tracking."""
        h, w = frame_shape[:2]
        max_dim = 640.0
        if max(h, w) > max_dim:
            return max_dim / max(h, w)
        return 1.0

    def init_tracker(self, frame: np.ndarray, prompt: dict, frame_number: int = 0):
        """
        Initialize the tracker with a starting frame and prompt dictionary.
        """
        try:
            self.label = prompt.get('label', 1)
            prompt_type = prompt.get('type', 'rectangle')
            
            if prompt_type == 'point':
                px, py = prompt['data']
                bbox = (px - 20, py - 20, 40, 40)
            else:
                bbox = prompt['data']
                
            h, w = frame.shape[:2]
            
            # Store original scale
            self.scale_factor = self._get_scale((h, w))
            if self.scale_factor < 1.0:
                frame_small = cv2.resize(frame, (int(w * self.scale_factor), int(h * self.scale_factor)), interpolation=cv2.INTER_AREA)
            else:
                frame_small = frame
                
            sh, sw = frame_small.shape[:2]
            
            x, y, bw, bh = bbox
            # Scale bbox down for tracking
            x, y = int(x * self.scale_factor), int(y * self.scale_factor)
            bw, bh = int(bw * self.scale_factor), int(bh * self.scale_factor)
            
            x = max(0, min(x, sw - 1))
            y = max(0, min(y, sh - 1))
            bw = max(1, min(bw, sw - x))
            bh = max(1, min(bh, sh - y))
            clamped_bbox = (x, y, bw, bh)

            # Create a fresh tracker instance (CSRT by default)
            self.tracker = CSRTTracker()
            success = self.tracker.init(frame_small, clamped_bbox)
            
            if success:
                self.is_tracking = True
                
                self.positive_points = []
                self._rel_pos_points = []
                for px, py in prompt.get('positive_points', []):
                    px_s, py_s = px * self.scale_factor, py * self.scale_factor
                    self.positive_points.append((int(px_s), int(py_s)))
                    self._rel_pos_points.append(((px_s - x) / bw, (py_s - y) / bh))
                    
                self.negative_points = []
                self._rel_neg_points = []
                for px, py in prompt.get('negative_points', []):
                    px_s, py_s = px * self.scale_factor, py * self.scale_factor
                    self.negative_points.append((int(px_s), int(py_s)))
                    self._rel_neg_points.append(((px_s - x) / bw, (py_s - y) / bh))
                
                self.state = TrackedFrameState(
                    frame_number=frame_number,
                    bounding_box=clamped_bbox,
                    positive_points=self.positive_points.copy(),
                    negative_points=self.negative_points.copy(),
                    confidence=1.0
                )
            else:
                self.is_tracking = False
                self.state = None
                
        except Exception as e:
            print(f"Failed to initialize tracker: {e}")
            self.is_tracking = False

    def update(self, frame: np.ndarray, frame_number: int) -> Optional[TrackedFrameState]:
        """
        Update the tracker with the next frame.
        Returns the TrackedFrameState if successful, None otherwise.
        """
        if not self.is_tracking or self.tracker is None:
            return None

        h, w = frame.shape[:2]
        if self.scale_factor < 1.0:
            frame_small = cv2.resize(frame, (int(w * self.scale_factor), int(h * self.scale_factor)), interpolation=cv2.INTER_AREA)
        else:
            frame_small = frame

        success, bbox, confidence = self.tracker.update(frame_small)
        
        if success:
            nx, ny, nw, nh = bbox
            
            self.positive_points = [
                (int(nx + rx * nw), int(ny + ry * nh)) 
                for rx, ry in self._rel_pos_points
            ]
            
            self.negative_points = [
                (int(nx + rx * nw), int(ny + ry * nh)) 
                for rx, ry in self._rel_neg_points
            ]
            
            self.state = TrackedFrameState(
                frame_number=frame_number,
                bounding_box=bbox,
                positive_points=self.positive_points.copy(),
                negative_points=self.negative_points.copy(),
                confidence=confidence
            )
            return self.state
        else:
            self.is_tracking = False
            self.state = None
            return None

    def reset(self):
        """Reset the tracker."""
        if self.tracker:
            self.tracker.reset()
        self.tracker = None
        self.state = None
        self.is_tracking = False
        self.positive_points = []
        self.negative_points = []
        self._rel_pos_points = []
        self._rel_neg_points = []

    def get_state(self) -> Optional[TrackedFrameState]:
        return self.state

    def get_sam_prompt(self, state: Optional[TrackedFrameState] = None) -> Optional[list]:
        """
        Get the prompt for SAM, optionally from a specific TrackedFrameState.
        Returns the prompt with ORIGINAL coordinates.
        """
        target_state = state if state is not None else self.state
        
        if target_state is None or target_state.bounding_box is None:
            return None
            
        if self.scale_factor < 1.0:
            inv_scale = 1.0 / self.scale_factor
            scaled_bbox = (
                int(target_state.bounding_box[0] * inv_scale),
                int(target_state.bounding_box[1] * inv_scale),
                int(target_state.bounding_box[2] * inv_scale),
                int(target_state.bounding_box[3] * inv_scale)
            )
        else:
            scaled_bbox = target_state.bounding_box
            
        x, y, w, h = scaled_bbox
        prompts = [{'type': 'rectangle', 'data': [x, y, x + w, y + h], 'label': self.label}]
        
        inv_scale = 1.0 / self.scale_factor if self.scale_factor < 1.0 else 1.0
        
        if target_state.positive_points or target_state.negative_points:
            for px, py in target_state.positive_points:
                prompts.append({
                    'type': 'point',
                    'data': [int(px * inv_scale), int(py * inv_scale)],
                    'label': 1
                })
            for px, py in target_state.negative_points:
                prompts.append({
                    'type': 'point',
                    'data': [int(px * inv_scale), int(py * inv_scale)],
                    'label': 0
                })
                
        return prompts
