import cv2
import numpy as np
import time
from core.ai.mask_candidate_selector import MaskCandidateSelector

class TwoPassSegmenter:
    """
    Sprint P4: Two-Pass Segmentation service.
    Runs a first inference pass, extracts the bounding box of the largest connected component,
    and runs a second inference pass combining the original points with the extracted bounding box.
    """

    def process(self, processor, frame, raw_prompts, initial_payload):
        start_time = time.perf_counter()
        selector = MaskCandidateSelector()

        # Pass 1
        t0_pass1 = time.perf_counter()
        rgbas1 = processor.process(frame, custom_prompt=initial_payload, quality_override="Best")
        pass1_latency = (time.perf_counter() - t0_pass1) * 1000

        if not isinstance(rgbas1, list) or len(rgbas1) == 0:
            alpha1 = rgbas1[:, :, 3] if rgbas1 is not None else None
            if alpha1 is None:
                return None, {"latency_ms": (time.perf_counter() - start_time) * 1000}, 0
            candidate_alphas = [alpha1]
        else:
            candidate_alphas = [rgba[:, :, 3] for rgba in rgbas1]

        result1 = selector.select_best_mask(candidate_alphas, raw_prompts, frame.shape[:2])
        if not result1:
            best_alpha1 = candidate_alphas[0]
        else:
            best_alpha1 = result1.selected_mask

        # Analysis: Extract bounding box of largest component
        binary = (best_alpha1 > 127).astype(np.uint8)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
        
        if num_labels <= 1:
            # No foreground object found in pass 1
            return best_alpha1, {"latency_ms": (time.perf_counter() - start_time) * 1000, "pass1_empty": True}, getattr(result1, 'candidate_index', 0)

        # Find largest component (excluding background at index 0)
        largest_idx = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        x = stats[largest_idx, cv2.CC_STAT_LEFT]
        y = stats[largest_idx, cv2.CC_STAT_TOP]
        w = stats[largest_idx, cv2.CC_STAT_WIDTH]
        h = stats[largest_idx, cv2.CC_STAT_HEIGHT]
        
        # Bounding box is [x1, y1, x2, y2]
        bbox = [int(x), int(y), int(x + w), int(y + h)]
        
        # Pass 2 Prompt Generation
        # Keep original positive/negative points, add the rectangle
        # initial_payload already contains the correctly scaled points.
        pass2_payload = []
        for p in initial_payload:
            if p["type"] == "point":
                pass2_payload.append(p)
        pass2_payload.append({"type": "rectangle", "data": bbox, "label": 1})

        # Pass 2
        t0_pass2 = time.perf_counter()
        rgbas2 = processor.process(frame, custom_prompt=pass2_payload, quality_override="Best")
        pass2_latency = (time.perf_counter() - t0_pass2) * 1000

        if not isinstance(rgbas2, list) or len(rgbas2) == 0:
            alpha2 = rgbas2[:, :, 3] if rgbas2 is not None else None
            candidate_alphas2 = [alpha2] if alpha2 is not None else []
        else:
            candidate_alphas2 = [rgba[:, :, 3] for rgba in rgbas2]
        
        if not candidate_alphas2:
            return best_alpha1, {"latency_ms": (time.perf_counter() - start_time) * 1000, "pass2_failed": True}, getattr(result1, 'candidate_index', 0)

        result2 = selector.select_best_mask(candidate_alphas2, raw_prompts, frame.shape[:2])
        if not result2:
            best_alpha2 = candidate_alphas2[0]
            candidate_index = 0
        else:
            best_alpha2 = result2.selected_mask
            candidate_index = result2.candidate_index
        
        total_latency = (time.perf_counter() - start_time) * 1000
        metadata = {
            "latency_ms": total_latency,
            "pass1_latency_ms": pass1_latency,
            "pass2_latency_ms": pass2_latency,
            "bbox": bbox
        }
        
        return best_alpha2, metadata, candidate_index
