from typing import Dict, Any, List

class QualityPredictor:
    """
    Predicts mask problems before they affect the user by analyzing
    confidence scores, edge risks, and tracking degradation trends.
    """
    def __init__(self):
        pass

    def predict_mask_quality(self, frame_index: int, motion_data: float, edge_complexity: float) -> Dict[str, Any]:
        """
        Calculates a predictive health score for a specific frame based on
        motion vectors and edge complexity, returning risk assessments.
        """
        confidence_score = max(0.0, min(100.0, 100.0 - (motion_data * 2.0) - (edge_complexity * 10.0)))
        
        edge_risk = "HIGH" if edge_complexity > 0.75 else "LOW"
        leakage_risk = "HIGH" if motion_data > 10.0 else "LOW"
        tracking_risk = "HIGH" if (motion_data > 15.0 or confidence_score < 50.0) else "LOW"
        
        # Color indicator for the timeline (green/yellow/red)
        health_color = "green"
        if confidence_score < 50.0 or tracking_risk == "HIGH":
            health_color = "red"
        elif confidence_score < 80.0 or edge_risk == "HIGH" or leakage_risk == "HIGH":
            health_color = "yellow"
            
        return {
            "frame": frame_index,
            "confidence_score": round(confidence_score, 1),
            "edge_risk": edge_risk,
            "leakage_risk": leakage_risk,
            "tracking_risk": tracking_risk,
            "timeline_health_indicator": health_color
        }

    def prioritize_smart_reviews(self, predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sorts the predicted issues to rank the most critical frames first,
        filtering out low-risk warnings to avoid unnecessary manual reviews.
        """
        # Filter only red and yellow frames
        issues = [p for p in predictions if p["timeline_health_indicator"] in ["red", "yellow"]]
        
        # Sort by confidence score (lowest first)
        issues.sort(key=lambda x: x["confidence_score"])
        
        return issues

    def check_predictive_reanchor(self, current_prediction: Dict[str, Any], trend_slope: float) -> bool:
        """
        Detects if tracking degradation is impending. If confidence is dropping rapidly
        (steep negative trend slope) while approaching a yellow state, triggers a preventative re-anchor.
        """
        # trend_slope is negative if confidence is decreasing
        if current_prediction["timeline_health_indicator"] == "yellow" and trend_slope < -5.0:
            return True
        return False
