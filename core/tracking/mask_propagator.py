import cv2
import numpy as np
from typing import Tuple, Optional

class MaskPropagator:
    """
    Stateless service to propagate a binary alpha mask from a previous frame
    to a current frame using bounding box transformations.
    """

    @staticmethod
    def propagate(
        previous_mask: np.ndarray,
        previous_bbox: Optional[Tuple[int, int, int, int]],
        current_bbox: Optional[Tuple[int, int, int, int]],
        frame_shape: Tuple[int, int]
    ) -> np.ndarray:
        """
        Propagates the mask based on bounding box changes.
        frame_shape should be (height, width).
        """
        h, w = frame_shape[:2]
        out_mask = np.zeros((h, w), dtype=np.uint8)

        if previous_bbox is None or current_bbox is None:
            return out_mask
        
        px, py, pw, ph = previous_bbox
        cx, cy, cw, ch = current_bbox

        if pw <= 0 or ph <= 0 or cw <= 0 or ch <= 0:
            return out_mask

        # 1. Clamp previous_bbox to mask boundaries safely
        ph_max, pw_max = previous_mask.shape[:2]
        
        px_start = max(0, int(px))
        py_start = max(0, int(py))
        px_end = min(pw_max, int(px + pw))
        py_end = min(ph_max, int(py + ph))
        
        # If the bounding box is completely outside the frame, return empty mask
        if px_start >= px_end or py_start >= py_end:
            return out_mask

        # Extract the region
        cropped_mask = previous_mask[py_start:py_end, px_start:px_end]

        # 2. Resize to current bbox dimensions
        if cropped_mask.size == 0:
            return out_mask
            
        # 3. Handle sub-pixel/rounding resizing carefully
        # The crop size might not exactly equal (pw, ph) due to boundary clamping,
        # so we calculate the proportional target size based on how much was clipped.
        # But for robust simple propagation, we can just resize the cropped area 
        # to the entire new bbox, or calculate exactly.
        
        # We'll calculate the target dimensions respecting the clamping ratio
        original_w_ratio = (px_end - px_start) / float(pw)
        original_h_ratio = (py_end - py_start) / float(ph)
        
        target_w = max(1, int(cw * original_w_ratio))
        target_h = max(1, int(ch * original_h_ratio))
        
        resized_mask = cv2.resize(cropped_mask, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        # 4. Place into current frame
        # Calculate offset in the new bounding box corresponding to where the crop started
        cx_offset = int((px_start - px) / float(pw) * cw)
        cy_offset = int((py_start - py) / float(ph) * ch)
        
        cx_start = max(0, int(cx + cx_offset))
        cy_start = max(0, int(cy + cy_offset))
        cx_end = cx_start + target_w
        cy_end = cy_start + target_h
        
        # Clip to output frame boundaries
        if cx_start < w and cy_start < h and cx_end > 0 and cy_end > 0:
            c_x1 = max(0, cx_start)
            c_y1 = max(0, cy_start)
            c_x2 = min(w, cx_end)
            c_y2 = min(h, cy_end)
            
            # Crop the resized mask if it goes out of bounds
            r_x1 = c_x1 - cx_start
            r_y1 = c_y1 - cy_start
            r_x2 = target_w - (cx_end - c_x2)
            r_y2 = target_h - (cy_end - c_y2)
            
            if r_x1 < r_x2 and r_y1 < r_y2:
                out_mask[c_y1:c_y2, c_x1:c_x2] = resized_mask[r_y1:r_y2, r_x1:r_x2]
            
        return out_mask
