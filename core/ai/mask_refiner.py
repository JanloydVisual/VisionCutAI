import cv2
import numpy as np

class MaskRefiner:
    """
    Applies edge-aware refinement to binary alpha masks to improve quality,
    reduce fragmentation, and smooth boundaries without introducing background leakage.
    """
    def __init__(self):
        self.kernel_size = 5
        
    def refine(self, mask: np.ndarray) -> np.ndarray:
        if mask is None or mask.size == 0:
            return mask
            
        # Ensure mask is uint8
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
            
        # 1. Fill small holes (Closing)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.kernel_size, self.kernel_size))
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 2. Edge-aware smoothing (Median Blur)
        # Preserves sharp edges while removing salt-and-pepper fragmentation on the boundary
        smoothed = cv2.medianBlur(closed, self.kernel_size)
        
        return smoothed
