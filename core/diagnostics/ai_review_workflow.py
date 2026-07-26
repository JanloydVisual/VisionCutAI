from typing import List, Dict, Any
from core.diagnostics.timeline_assistant import AITimelineAssistant

class AIReviewWorkflow:
    """
    Manages the guided AI mask refinement process, bridging diagnostic data
    with one-click mask re-generation and comparison capabilities.
    """
    def __init__(self, timeline_assistant: AITimelineAssistant):
        self.assistant = timeline_assistant
        self.reviewed_frames = set()

    def get_issue_list(self) -> List[Dict]:
        return self.assistant.scan_timeline_for_issues()
        
    def send_to_refinement(self, frame_index: int):
        """Mock functionality: Triggers InteractiveMaskWorker specifically for this frame."""
        pass
        
    def mark_reviewed(self, frame_index: int):
        self.reviewed_frames.add(frame_index)

    def generate_comparison_masks(self, frame_index: int) -> Dict[str, Any]:
        """Returns mock 'before' and 'after' mask representations for the viewer."""
        return {
            "before_mask": None, # Mock binary mask
            "after_mask": None   # Mock refined alpha mask
        }

    def get_approval_status(self) -> Dict[str, Any]:
        issues = self.get_issue_list()
        total_issues = len(issues)
        reviewed = len(self.reviewed_frames)
        
        ready = (total_issues == 0) or (reviewed >= total_issues)
        score = 100.0 if total_issues == 0 else (reviewed / total_issues) * 100.0
        
        return {
            "reviewed_count": reviewed,
            "total_issues": total_issues,
            "quality_score": score,
            "ready_for_export": ready
        }
