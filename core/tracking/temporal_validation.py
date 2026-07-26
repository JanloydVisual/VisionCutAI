import time
import numpy as np
import cv2
from core.ai.anchor_manager import AnchorState, QualityGrade
from core.controller import AppController
from core.tracking.temporal_metrics import TemporalMetricsCollector

class TemporalValidationRunner:
    def __init__(self, controller: AppController):
        self.controller = controller

    def run_validation(self, video_path: str, anchor_frame: int, initial_bbox: tuple, max_frames: int = 60) -> TemporalMetricsCollector:
        print(f"\n[Validation] Starting temporal validation on {video_path} at frame {anchor_frame}")
        self.controller.open_video(video_path)
        self.controller.seek(anchor_frame)
        frame = self.controller.video.get_frame(anchor_frame)

        if frame is None:
            raise Exception(f"Failed to load frame {anchor_frame}")

        # 3. Run the existing MobileSAM pipeline
        prompt = {"type": "rectangle", "data": initial_bbox, "label": 1,
                  "positive_points": [], "negative_points": []}
                  
        self.controller._background_removal_processor.sam_prompt = [prompt]
        mask_pil = self.controller._background_removal_processor.process(frame)
        
        if mask_pil is None:
            raise Exception("MobileSAM failed to generate initial mask.")
            
        mask = np.array(mask_pil)
        mask = np.array(mask_pil)
        mask = np.squeeze(mask)
        if len(mask.shape) == 3 and mask.shape[2] == 4:
            mask = mask[:, :, 3]
        # 4. Create AnchorState
        anchor = AnchorState(
            frame_number=anchor_frame,
            mask=mask,
            bounding_box=initial_bbox,
            positive_points=[],
            negative_points=[],
            quality_grade=QualityGrade.GOOD
        )
        self.controller.tracking_engine.anchor_manager.clear()
        self.controller.tracking_engine.anchor_manager.add_anchor(anchor)
        
        self.controller.object_tracker.init_tracker(frame, prompt)
        
        # We need to capture failures
        failure_reason = None
        def on_tracking_paused(frame_num, conf_result):
            nonlocal failure_reason
            reason_str = conf_result.reasons if conf_result else 'Tracker None'
            failure_reason = f"Paused at {frame_num} - {reason_str}"
            
        def on_tracking_failed(err):
            nonlocal failure_reason
            failure_reason = f"Crashed: {err}"
            
        self.controller.tracking_engine.tracking_paused.connect(on_tracking_paused)
        self.controller.tracking_engine.tracking_failed.connect(on_tracking_failed)

        # 5. Start TrackingEngine propagation
        self.controller.tracking_engine.start_tracking(anchor_frame, anchor_frame + max_frames)
        
        while self.controller.tracking_engine._is_running:
            time.sleep(0.1)
            
        self.controller.tracking_engine.tracking_paused.disconnect(on_tracking_paused)
        self.controller.tracking_engine.tracking_failed.disconnect(on_tracking_failed)
        
        metrics = self.controller.tracking_engine.metrics
        metrics.print_report()
        
        if failure_reason:
            print(f"Validation ended with failure: {failure_reason}")
            
        # For every propagated frame collect:
        print("\n--- Per-Frame Collection ---")
        for log in metrics.frame_logs:
            print(f"Frame {log['frame_index']} | {log['tracker_type']} | Latency: {log['latency']:.1f}ms | IoU: {log['iou']:.3f} | Area Change: {log['area_change']:.3f} | BBox Move: {log['bbox_movement']:.1f}px | Conf: {log['confidence_result']}")
            
        return metrics
