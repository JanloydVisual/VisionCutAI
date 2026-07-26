import cv2
import numpy as np
from core.ai.models import QualityGrade, EvaluationResult, RefinementHint, RefinementHintType

            'gate': gate,
            'largest_component_ratio': round(largest_component_ratio, 3),
            'secondary_component_ratio': round(secondary_component_ratio, 3),
            'fragmentation': fragmentation,
            'prompt_overlap': round(prompt_overlap, 3),
            'mask_area': round(mask_area, 4),
            'edge_continuity': round(edge_continuity, 3),
            'reasons': reasons,
        }

        # Generate negative hints for secondary components
        hints = []
        if len(comps) > 1:
            for idx, area in comps[1:4]: # Top 3 secondary components
                cx, cy = centroids[idx]
                hints.append(RefinementHint(
                    position=(int(cx), int(cy)),
                    hint_type=RefinementHintType.ADD_NEGATIVE,
                    confidence=0.8,
                    reason=f"Secondary component (area {area})"
                ))

        return EvaluationResult(grade=gate, hints=hints, metrics=metrics)

    def evaluate_quality_gate(self, alpha, prompts_used, frame_shape) -> EvaluationResult:
