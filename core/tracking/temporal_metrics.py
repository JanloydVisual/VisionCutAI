import numpy as np

class TemporalMetricsCollector:
    def __init__(self):
        self.propagated_frame_count = 0
        self.anchor_count = 0
        self.mobile_sam_call_count = 0
        self.reanchor_count = 0
        self.anchor_frame = 0
        
        self.tracker_name = "Unknown"
        self.automatic_reanchors_successful = 0
        self.automatic_reanchors_failed = 0
        self.sam_calls_from_reanchor = 0
        
        self.tracker_false_positive_rejections = 0
        self.mask_validation_failures = 0
        self.validation_confidence_sum = 0.0
        self.validation_confidence_count = 0
        
        self.total_iou = 0.0
        self.sam_calls_from_reanchor = 0
        
        self.total_propagation_latency_ms = 0.0
        self.frame_logs = []
        self.minimum_mask_iou = 1.0
        self.maximum_mask_iou = 0.0
        self.total_propagation_latency_ms = 0.0
        self.frame_logs = []
        
        self.optical_flow_frames = 0
        self.total_flow_confidence = 0.0

    def add_optical_flow(self, confidence: float):
        self.optical_flow_frames += 1
        self.total_flow_confidence += confidence
        
    def add_anchor(self, frame_index=0):
        self.mobile_sam_call_count += 1
        
    def add_reanchor(self):
        self.reanchor_count += 1
        self.anchor_count += 1
        self.mobile_sam_call_count += 1
    def record_propagation(self, previous_mask: np.ndarray, current_mask: np.ndarray, latency_ms: float, 
                           frame_index: int = 0, prev_bbox: tuple = None, curr_bbox: tuple = None, conf_result = None):
        self.propagated_frame_count += 1
        self.total_propagation_latency_ms += latency_ms
        
        iou = 0.0
        area_change = 0.0
        bbox_movement = 0.0
        
        if prev_bbox and curr_bbox:
            px, py, pw, ph = prev_bbox
            cx, cy, cw, ch = curr_bbox
            pcx, pcy = px + pw/2, py + ph/2
            ccx, ccy = cx + cw/2, cy + ch/2
            bbox_movement = ((pcx - ccx)**2 + (pcy - ccy)**2)**0.5
            
        if previous_mask is not None and current_mask is not None:
            prev_area = (previous_mask > 0).sum()
            curr_area = (current_mask > 0).sum()
            if prev_area > 0:
                area_change = abs(curr_area - prev_area) / prev_area
                
            # Calculate IoU
            intersection = np.logical_and(previous_mask > 0, current_mask > 0).sum()
            union = np.logical_or(previous_mask > 0, current_mask > 0).sum()
            
            if union > 0:
                iou = intersection / union
                self.total_iou += iou
                self.minimum_mask_iou = min(self.minimum_mask_iou, iou)
    def get_average_flow_confidence(self) -> float:
        if self.optical_flow_frames == 0:
            return 0.0
        return self.total_flow_confidence / self.optical_flow_frames

    def get_mask_iou_after_flow(self) -> float:
        flow_ious = [log['iou'] for log in self.frame_logs if log['tracker_type'] == 'OpticalFlow']
        if not flow_ious:
            return 0.0
        return sum(flow_ious) / len(flow_ious)

    def print_report(self):
        print("\n--- Real Temporal Propagation Report ---\n")
        print(f"Anchor frame: {self.anchor_frame}")
        total_frames = self.propagated_frame_count + self.anchor_count
        print(f"Total frames: {total_frames}")
        print(f"Tracker: {self.tracker_name}")
        print(f"SAM calls: {self.mobile_sam_call_count}")
        print(f"Propagation frames: {self.propagated_frame_count}")
        print(f"Optical flow frames: {self.optical_flow_frames}\n")
        print(f"Average IoU: {self.get_average_stability_iou():.3f}")
        min_iou = self.minimum_mask_iou if self.propagated_frame_count > 0 else 0.0
        print(f"Minimum IoU: {min_iou:.3f}")
        frames_before_failure = self.frames_before_pause if self.frames_before_pause >= 0 else self.propagated_frame_count
        print(f"Frames before failure: {frames_before_failure}")
        print(f"Average latency: {self.get_average_latency_ms():.2f} ms")
        if self.optical_flow_frames > 0:
            print(f"Average flow confidence: {self.get_average_flow_confidence():.3f}")
            print(f"Mask IoU after flow: {self.get_mask_iou_after_flow():.3f}")
        print("\n-----------------------------------")
            'iou': iou,
            'area_change': area_change,
            'bbox_movement': bbox_movement,
            'confidence_result': conf_result.is_confident if conf_result else False
        })
            changed = np.logical_xor(previous_mask > 0, current_mask > 0).sum()
            total_pixels = previous_mask.size
            
            if total_pixels > 0:
                self.total_changed_pixel_ratio += changed / total_pixels

    def get_average_stability_iou(self) -> float:
        if self.propagated_frame_count == 0:
            return 0.0
        return sum(flow_ious) / len(flow_ious)

    def get_average_validation_confidence(self):
        if self.validation_confidence_count == 0:
            return 0.0
        return self.validation_confidence_sum / self.validation_confidence_count
        return self.total_changed_pixel_ratio / self.propagated_frame_count
        
        if self.validation_confidence_count == 0:
            return 0.0
        return self.validation_confidence_sum / self.validation_confidence_count

    def print_report(self):
        return self.total_propagation_latency_ms / self.propagated_frame_count

    def print_report(self):
    def print_report(self):
        print("\n--- Real Temporal Propagation Report ---\n")
        print(f"Optical flow frames: {self.optical_flow_frames}\n")
        print(f"False tracker states: {self.tracker_false_positive_rejections}")
        print(f"Rejected: {self.mask_validation_failures}")
        print(f"Automatic reanchors: {self.automatic_reanchors_attempted}")
        print(f"Successful recoveries: {self.automatic_reanchors_successful}\n")
        print(f"Average IoU: {self.get_average_stability_iou():.3f}")
        print(f"Minimum IoU: {min_iou:.3f}")
        frames_before_failure = self.frames_before_pause if self.frames_before_pause >= 0 else self.propagated_frame_count
        print(f"Frames before failure: {frames_before_failure}")
        print(f"Average latency: {self.get_average_latency_ms():.2f} ms")
        print(f"Average IoU: {self.get_average_stability_iou():.3f}")
        min_iou = self.minimum_mask_iou if self.propagated_frame_count > 0 else 0.0
        print(f"Minimum IoU: {min_iou:.3f}")
        frames_before_failure = self.frames_before_pause if self.frames_before_pause >= 0 else self.propagated_frame_count
        print(f"Frames before failure: {frames_before_failure}")
        print(f"Average latency: {self.get_average_latency_ms():.2f} ms\n")
        print("-----------------------------------")