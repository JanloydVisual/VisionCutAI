import time
from typing import Dict, Any, List

class UserTelemetryEngine:
    """
    Collects workflow telemetry, maps hardware profiles, and generates
    beta user feedback reports to improve the first-time user experience.
    """
    def __init__(self):
        self.session_start = time.time()
        self.time_to_first_mask = -1.0
        self.time_to_first_export = -1.0
        self.failed_actions = 0
        self.repeated_actions = 0
        self.action_history = []
        
    def log_action(self, action_name: str, success: bool):
        self.action_history.append(action_name)
        if not success:
            self.failed_actions += 1
            
        # Check repeated actions (simple mock: last 3 are identical)
        if len(self.action_history) >= 3:
            if self.action_history[-1] == self.action_history[-2] == self.action_history[-3]:
                self.repeated_actions += 1

        if action_name == "create_mask" and success and self.time_to_first_mask < 0:
            self.time_to_first_mask = time.time() - self.session_start
            
        if action_name == "export_project" and success and self.time_to_first_export < 0:
            self.time_to_first_export = time.time() - self.session_start

    def detect_hardware_profile(self) -> str:
        """
        Profiles the user's hardware.
        Mock: Returns 'RTX_3050_4GB', 'MID_RANGE', or 'HIGH_END'
        """
        # For testing, return entry level
        return "RTX_3050_4GB"

    def generate_feedback_report(self) -> Dict[str, Any]:
        """
        Compiles the full beta telemetry session into a transmittable report.
        """
        return {
            "hardware_profile": self.detect_hardware_profile(),
            "time_to_first_mask_sec": round(self.time_to_first_mask, 2),
            "time_to_first_export_sec": round(self.time_to_first_export, 2),
            "failed_actions_count": self.failed_actions,
            "repeated_actions_count": self.repeated_actions,
            "total_session_time_sec": round(time.time() - self.session_start, 2)
        }
