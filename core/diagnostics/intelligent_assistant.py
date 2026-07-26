from typing import Dict, Any, List

class IntelligentAssistantLayer:
    """
    Acts as a high-level orchestration layer, translating complex AI quality
    predictions into simple, actionable recommendations for the user,
    and enabling one-click repairs.
    """
    def __init__(self, quality_predictor=None):
        self.predictor = quality_predictor
        self.active_recommendations = []
        self.activity_log = []

    def generate_recommendations(self, frame_predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parses raw QualityPredictor output into actionable UX recommendations.
        """
        self.active_recommendations = []
        for pred in frame_predictions:
            if pred["timeline_health_indicator"] == "red":
                self.active_recommendations.append({
                    "frame": pred["frame"],
                    "type": "CRITICAL_TRACKING_LOSS",
                    "message": "Tracking severely degraded. Immediate manual anchor required.",
                    "action": "add_anchor"
                })
            elif pred["edge_risk"] == "HIGH":
                self.active_recommendations.append({
                    "frame": pred["frame"],
                    "type": "EDGE_LEAKAGE",
                    "message": "High edge complexity detected. Fine-detail refinement stroke suggested.",
                    "action": "refine_edge"
                })
        return self.active_recommendations

    def fix_critical_issue(self, recommendation: Dict[str, Any]) -> bool:
        """
        Mock executes a one-click repair utilizing existing backend systems.
        """
        self.activity_log.append(f"Auto-repair executed for frame {recommendation['frame']}: {recommendation['action']}")
        return True

    def calculate_export_readiness(self, frame_predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes a comprehensive score indicating how safe the timeline is to export.
        """
        if not frame_predictions:
            return {"score": 100, "status": "READY", "unresolved_issues": 0}

        red_count = sum(1 for p in frame_predictions if p["timeline_health_indicator"] == "red")
        yellow_count = sum(1 for p in frame_predictions if p["timeline_health_indicator"] == "yellow")
        
        avg_confidence = sum(p["confidence_score"] for p in frame_predictions) / len(frame_predictions)
        
        # Calculate a readiness score (0-100)
        score = max(0.0, avg_confidence - (red_count * 10) - (yellow_count * 2))
        
        status = "READY"
        if score < 70 or red_count > 0:
            status = "NEEDS_REVIEW"
            
        return {
            "score": round(score, 1),
            "status": status,
            "unresolved_critical_issues": red_count,
            "unresolved_warnings": yellow_count
        }

    def get_ai_explanation_panel_data(self) -> Dict[str, Any]:
        """Returns readable logs explaining exactly what the AI backend is doing."""
        return {
            "recent_activity": self.activity_log[-5:], # Show last 5 actions
            "status_message": "AI Assistant is monitoring the timeline."
        }
