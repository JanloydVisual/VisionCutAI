import math
from dataclasses import dataclass
from typing import Tuple, List, Optional

@dataclass
class TrackingConfidenceResult:
    is_confident: bool
    confidence_score: float
    reasons: List[str]

class TrackingConfidenceEvaluator:
    def __init__(self):
        # Thresholds
        self.min_tracker_confidence = 0.6
        self.max_area_change_ratio = 0.5  # Max 50% change in area per frame
        self.max_aspect_ratio_change = 0.5 # Max 50% change in aspect ratio per frame
        
        # We can also track velocity if we store a history, but for now we just compare to previous frame.
        self.max_movement_ratio = 0.5 # Max movement relative to bounding box size

    def evaluate(self, previous_bbox: Optional[Tuple[int, int, int, int]], 
                 current_bbox: Optional[Tuple[int, int, int, int]], 
                 tracker_state) -> TrackingConfidenceResult:
        """
        Evaluate if the tracker is still confidently tracking the object.
        tracker_state is expected to be a TrackedFrameState or similar object that provides 'confidence'.
        """
        reasons = []
        is_confident = True
        
        # 1. Check raw tracker confidence
        confidence_score = getattr(tracker_state, 'confidence', 1.0)
        if confidence_score < self.min_tracker_confidence:
            is_confident = False
            reasons.append(f"Raw tracker confidence too low ({confidence_score:.2f} < {self.min_tracker_confidence})")
            
        # If we lost the bounding box entirely, it's an immediate fail
        if current_bbox is None or current_bbox[2] <= 0 or current_bbox[3] <= 0:
            return TrackingConfidenceResult(False, 0.0, ["Invalid bounding box"])
            
        cx, cy, cw, ch = current_bbox
        current_area = cw * ch
        current_aspect = cw / float(max(ch, 1))
            
        # 2. Check heuristics against previous frame
        if previous_bbox is not None and previous_bbox[2] > 0 and previous_bbox[3] > 0:
            px, py, pw, ph = previous_bbox
            prev_area = pw * ph
            prev_aspect = pw / float(max(ph, 1))
            
            # Area change
            area_ratio = abs(current_area - prev_area) / float(prev_area)
            if area_ratio > self.max_area_change_ratio:
                is_confident = False
                reasons.append(f"Area changed by {area_ratio*100:.0f}% (threshold {self.max_area_change_ratio*100:.0f}%)")
                
            # Aspect ratio change
            aspect_change = abs(current_aspect - prev_aspect) / float(prev_aspect)
            if aspect_change > self.max_aspect_ratio_change:
                is_confident = False
                reasons.append(f"Aspect ratio changed by {aspect_change*100:.0f}%")
                
            # Movement velocity (center point displacement)
            p_center_x, p_center_y = px + pw/2, py + ph/2
            c_center_x, c_center_y = cx + cw/2, cy + ch/2
            
            distance = math.sqrt((c_center_x - p_center_x)**2 + (c_center_y - p_center_y)**2)
            # Normalize distance by object size (diagonal)
            obj_size = math.sqrt(pw**2 + ph**2)
            movement_ratio = distance / float(max(obj_size, 1))
            
            if movement_ratio > self.max_movement_ratio:
                is_confident = False
                reasons.append(f"Excessive movement ({movement_ratio*100:.0f}% of object size)")
                
        return TrackingConfidenceResult(
            is_confident=is_confident,
            confidence_score=confidence_score,
            reasons=reasons
        )
