from typing import Dict, Any, List

class BetaUXManager:
    """
    Orchestrates the onboarding experience, safety warnings, and contextual help
    for beta users without modifying underlying pipeline code.
    """
    def __init__(self):
        self.onboarding_completed = False
        self.ux_telemetry = []

    def get_onboarding_tutorial(self, current_step: str) -> Dict[str, str]:
        """Provides dynamic tutorial steps based on user progress."""
        if current_step == "import":
            return {"hint": "Drag and drop your video file here to begin."}
        elif current_step == "workflow_selection":
            return {"hint": "Select Talking Head, Real Estate, or Product to optimize the AI."}
        elif current_step == "magic_mask":
            return {"hint": "Draw a green stroke over your subject to create the initial mask."}
        
        self.onboarding_completed = True
        return {"hint": "You're ready to export!"}

    def get_contextual_tooltip(self, ui_element: str) -> str:
        """Centralized dictionary of UI tooltips."""
        tooltips = {
            "btn_export_resolve": "Export a transparent PNG sequence formatted for DaVinci Resolve.",
            "btn_smart_review": "Jump to frames where tracking confidence is low.",
            "btn_predictive_anchor": "Manually force a MobileSAM re-anchor to fix drifting masks."
        }
        return tooltips.get(ui_element, "")

    def run_safety_checks(self, project_state: Dict[str, Any]) -> List[str]:
        """Prevents users from executing destructive or useless actions."""
        warnings = []
        if not project_state.get("has_video"):
            warnings.append("MISSING_VIDEO")
        elif not project_state.get("has_mask"):
            warnings.append("MISSING_MASK")
            
        if project_state.get("unresolved_critical_issues", 0) > 0:
            warnings.append("EXPORT_NOT_RECOMMENDED_RED_FRAMES")
            
        return warnings

    def log_ux_event(self, event_name: str, friction_level: int = 0):
        """Records UI interactions to identify confusing interface elements."""
        self.ux_telemetry.append({
            "event": event_name,
            "friction": friction_level # 0 = smooth, 5 = user repeatedly failed
        })
        
    def get_friction_report(self) -> Dict[str, Any]:
        """Aggregates telemetry for developer review."""
        total_friction = sum(e["friction"] for e in self.ux_telemetry)
        return {
            "total_events": len(self.ux_telemetry),
            "accumulated_friction": total_friction,
            "onboarding_completed": self.onboarding_completed
        }
