from typing import List, Dict

class AITimelineAssistant:
    """
    Analyzes the timeline to locate tracking issues, cache misses, and low-quality masks,
    assisting the user in navigating directly to frames requiring manual review.
    """
    def __init__(self, timeline, tracking_engine):
        self.timeline = timeline
        self.tracking_engine = tracking_engine
        self.issues = []

    def scan_timeline_for_issues(self) -> List[Dict]:
        """Mock scan: returns list of problematic frames"""
        self.issues = [
            {"frame": 105, "type": "tracking_failure", "description": "Tracking confidence dropped below threshold"},
            {"frame": 210, "type": "low_quality", "description": "High edge fragmentation detected"},
            {"frame": 350, "type": "cache_miss", "description": "Frame missing from render cache"}
        ]
        return self.issues

    def get_next_issue(self, current_frame: int) -> int:
        for issue in sorted(self.issues, key=lambda x: x["frame"]):
            if issue["frame"] > current_frame:
                return issue["frame"]
        return -1
        
    def get_previous_issue(self, current_frame: int) -> int:
        for issue in sorted(self.issues, key=lambda x: x["frame"], reverse=True):
            if issue["frame"] < current_frame:
                return issue["frame"]
        return -1

    def get_export_readiness(self) -> dict:
        total_frames = 1000  # Mock
        issue_frames = len(self.issues)
        coverage = 100.0 if total_frames == 0 else ((total_frames - issue_frames) / total_frames) * 100
        
        return {
            "mask_coverage": coverage,
            "tracking_stability": 92.5,
            "frames_requiring_review": issue_frames
        }
