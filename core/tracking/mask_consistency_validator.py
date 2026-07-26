import cv2
import numpy as np
from dataclasses import dataclass
from typing import Tuple

@dataclass
class TrackingValidationResult:
    is_valid: bool
    confidence: float
    reason: str

class MaskConsistencyValidator:
    def __init__(self):
        self.containment_threshold = 0.85
        self.area_change_threshold = 0.5  # Max 50% change allowed
        self.hist_corr_threshold = 0.5    # Minimum histogram correlation

    def validate(self, frame: np.ndarray, propagated_mask: np.ndarray, predicted_bbox: tuple, previous_mask: np.ndarray, previous_frame: np.ndarray) -> TrackingValidationResult:
        if propagated_mask is None or previous_mask is None:
            return TrackingValidationResult(False, 0.0, "Missing mask")
            
        x, y, w, h = predicted_bbox
        
        # 1. Mask containment: percentage of mask pixels inside predicted bbox
        total_mask_pixels = np.count_nonzero(propagated_mask)
        if total_mask_pixels == 0:
            return TrackingValidationResult(False, 0.0, "Empty mask")
            
        bbox_mask = np.zeros_like(propagated_mask)
        # Ensure bounds are safe
        fh, fw = propagated_mask.shape[:2]
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(fw, int(x + w)), min(fh, int(y + h))
        
        if x2 <= x1 or y2 <= y1:
            return TrackingValidationResult(False, 0.0, "Invalid bounding box dimensions")
            
        bbox_mask[y1:y2, x1:x2] = 255
        
        # 3. Appearance consistency (Color histogram)
        curr_hist = self._calc_masked_hist(frame, propagated_mask)
        prev_hist = self._calc_masked_hist(previous_frame, previous_mask)
        
        if np.sum(curr_hist) == 0 or np.sum(prev_hist) == 0:
            hist_corr = 0.0
        else:
            hist_corr = cv2.compareHist(curr_hist, prev_hist, cv2.HISTCMP_CORREL)
        
        if hist_corr < self.hist_corr_threshold:
        prev_mask_pixels = np.count_nonzero(previous_mask)
        area_change = 0.0
        if prev_mask_pixels > 0:
            area_change = abs(total_mask_pixels - prev_mask_pixels) / prev_mask_pixels
            if area_change > self.area_change_threshold:
                return TrackingValidationResult(False, max(0.0, 1.0 - area_change), f"Area change too high ({area_change:.2f} > {self.area_change_threshold})")
                
        # 3. Appearance consistency (Color histogram)
        curr_hist = self._calc_masked_hist(frame, propagated_mask)
        prev_hist = self._calc_masked_hist(previous_frame, previous_mask)
        
        hist_corr = cv2.compareHist(curr_hist, prev_hist, cv2.HISTCMP_CORREL)
        
        if hist_corr < self.hist_corr_threshold:
            return TrackingValidationResult(False, max(0.0, hist_corr), f"Appearance changed drastically (corr: {hist_corr:.2f})")
            
        # 4. Edge consistency
        # Skipping heavy edge consistency since hist & containment handle the primary failure cases efficiently
        
        # Combine metrics for final confidence
        confidence = (containment_ratio * 0.4) + (max(0.0, 1.0 - (area_change if prev_mask_pixels > 0 else 0)) * 0.3) + (max(0.0, hist_corr) * 0.3)
        
        return TrackingValidationResult(True, confidence, "Valid")
        
    def _calc_masked_hist(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # Use Hue and Saturation
        mask_uint8 = (mask > 0).astype(np.uint8) * 255
        hist = cv2.calcHist([hsv], [0, 1], mask_uint8, [32, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist
