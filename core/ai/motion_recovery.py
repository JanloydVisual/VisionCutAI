import cv2
import numpy as np
from typing import Dict, Tuple

class MotionRecoveryEngine:
    """
    Advanced Edge and Motion Recovery:
    Handles motion blur detection, fine edge refinement, and temporal mask stabilization.
    """
    def __init__(self):
        self.history_mask = None

    def detect_motion_blur(self, frame: np.ndarray, prev_frame: np.ndarray) -> Dict[str, float]:
        """
        Calculates frame-to-frame motion to infer blur probability and tracking confidence.
        """
        if prev_frame is None or frame is None:
            return {"motion_magnitude": 0.0, "confidence_penalty": 0.0}

        gray1 = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        flow = cv2.calcOpticalFlowFarneback(gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        avg_motion = np.mean(mag)
        
        # High motion > more blur > lower confidence
        penalty = min(0.5, avg_motion / 50.0) 
        
        return {
            "motion_magnitude": float(avg_motion),
            "confidence_penalty": float(penalty)
        }

    def refine_fine_details(self, mask: np.ndarray) -> np.ndarray:
        """
        Enhances thin edges and preserves small structures (like hair/fur)
        using morphological operations.
        """
        # A mock implementation of edge-aware detail preservation
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        # Top Hat gives us the fine details that might have been lost
        tophat = cv2.morphologyEx(mask, cv2.MORPH_TOPHAT, kernel)
        
        # Add the fine details back to the base mask
        refined = cv2.add(mask, tophat)
        return refined

    def stabilize_temporal_edges(self, mask: np.ndarray) -> np.ndarray:
        """
        Reduces mask flicker between consecutive frames by bleeding the previous
        stable mask into the current one slightly.
        """
        if self.history_mask is None:
            self.history_mask = mask.copy()
            return mask
            
        # Blend 80% current, 20% previous to reduce temporal flicker
        stabilized = cv2.addWeighted(mask, 0.8, self.history_mask, 0.2, 0)
        self.history_mask = stabilized.copy()
        
        return stabilized
