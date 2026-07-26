import numpy as np
import cv2
from core.ai.anchor_manager import AnchorState
class ReanchorManager:
    def __init__(self, bg_processor, evaluator: SegmentationEvaluator):
        self.bg_processor = bg_processor
        self.evaluator = evaluator

    def attempt_reanchor(self, frame: np.ndarray, predicted_mask: np.ndarray, predicted_bbox: tuple, anchor_state: AnchorState, frame_number: int):
        """
        Attempts to automatically re-anchor MobileSAM on a tracking failure.
        """
        if predicted_bbox is None or predicted_bbox == (0, 0, 0, 0):
            return False, None
            
        x, y, w, h = predicted_bbox
        cx, cy = int(x + w / 2), int(y + h / 2)
        
        # 2. Generate temporary SAM prompts
        prompt = {
            "type": "rectangle",
            "data": predicted_bbox,
            "label": 1,
            "positive_points": [[cx, cy]],
            "negative_points": anchor_state.negative_points if anchor_state else []
        }
        
        # Evaluate the predicted (failed) mask to establish a baseline
        prev_eval = self.evaluator.evaluate_quality_gate(predicted_mask, [prompt], frame.shape)
        
        # 3. Run MobileSAM through existing inference pipeline
        # Store original prompt state to restore it later if needed (to not corrupt session)
        original_prompt = self.bg_processor.sam_prompt
        self.bg_processor.sam_prompt = [prompt]
        mask_pil = self.bg_processor.process(frame)
        self.bg_processor.sam_prompt = original_prompt
        
        if mask_pil is None:
            return False, None
            
        mask = np.array(mask_pil)
        mask = np.squeeze(mask)
        if len(mask.shape) == 3 and mask.shape[2] == 4:
            mask = mask[:, :, 3]
            
        # 4. Evaluate result using SegmentationEvaluator
        new_eval = self.evaluator.evaluate_quality_gate(mask, [prompt], frame.shape)
        grade_improves = new_rank >= prev_rank
        leakage_decreases = new_leakage <= prev_leakage
        
        print(f"[DEBUG-REANCHOR] Frame {frame_number}")
        print(f"  Prev Grade: {prev_eval.grade} (Rank: {prev_rank}), New Grade: {new_eval.grade} (Rank: {new_rank}) -> Improves: {grade_improves}")
        print(f"  Prev Leakage: {prev_leakage:.3f}, New Leakage: {new_leakage:.3f} -> Decreases: {leakage_decreases}")
        
        # Mask area is reasonable: e.g. at least 1% of frame and not 95% of frame
        h_f, w_f = frame.shape[:2]
        frame_area = h_f * w_f
        mask_area = np.count_nonzero(mask)
        # Mask area is reasonable: e.g. at least 0.1% of frame and not 95% of frame
        h_f, w_f = frame.shape[:2]
        frame_area = h_f * w_f
        mask_area = np.count_nonzero(mask)
        if grade_improves and leakage_decreases and area_reasonable:
            # Calculate correct bounding box from the generated mask
            mask_uint8 = (mask > 0).astype(np.uint8) * 255
            x_m, y_m, w_m, h_m = cv2.boundingRect(mask_uint8)
            new_bbox = (x_m, y_m, w_m, h_m)
            
            new_anchor = AnchorState(
                frame_number=frame_number,
                mask=mask,
                bounding_box=new_bbox,
                positive_points=[(cx, cy)],
                negative_points=prompt["negative_points"],
                quality_grade=new_eval.grade
            )
            return True, new_anchor
                bounding_box=predicted_bbox,
                positive_points=[(cx, cy)],
                negative_points=prompt["negative_points"],
                quality_grade=new_eval.grade
            )
            return True, new_anchor
            
        return False, None
