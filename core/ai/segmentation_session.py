from typing import List
from core.ai.models import QualityGrade, EvaluationResult, RefinementHint

class SegmentationSession:
    def __init__(self):
        self.current_frame = None
        self.current_mask = None
        self.confidence_info = None
        self.quality_grade = None
        self.refinement_hints: List[RefinementHint] = []
        self.overlay_enabled = True

    def begin_new_frame(self, frame):
        self.current_frame = frame
        self.current_mask = None
        self.confidence_info = None
        self.quality_grade = None
        self.refinement_hints = []
