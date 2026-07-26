import json
from typing import Dict, Any

class SessionReportGenerator:
    """
    Generates a VisionCut_Session_Report.json containing workflow metrics.
    """
    def __init__(self, output_path: str = "VisionCut_Session_Report.json"):
        self.output_path = output_path
        self.data: Dict[str, Any] = {
            "video_duration_sec": 0,
            "objects_created": 0,
            "tracking_frames": 0,
            "reanchors": 0,
            "refinements": 0,
            "export_status": "Not Started",
            "processing_time_sec": 0.0
        }
        
    def generate(self):
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)
        return self.output_path
