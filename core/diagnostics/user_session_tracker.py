import json
from typing import Dict, Any

class UserSessionTracker:
    """
    Monitors user workflow friction and timing metrics to evaluate UX quality.
    """
    def __init__(self, output_path: str = "VisionCut_User_Report.json"):
        self.output_path = output_path
        self.metrics: Dict[str, Any] = {
            "import_time_sec": 0.0,
            "first_mask_creation_time_sec": 0.0,
            "first_good_mask_time_sec": 0.0,
            "refinement_click_count": 0,
            "undo_redo_usage": 0,
            "preset_changes": 0,
            "tracking_pauses": 0,
            "manual_reanchors": 0,
            "export_completion": False
        }
        
    def generate_report(self):
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=4)
        return self.output_path
