from typing import Dict, Any

class MagicMaskOverlayUI:
    """
    Manages the core interactive visual experience for the paint-to-mask workflow.
    Handles stroke colors, AI processing state transitions, and live confidence readouts.
    """
    def __init__(self):
        self.stroke_type = "positive" # "positive" or "negative"
        self.processing_state = "idle" # "idle", "processing", "transitioning"
        self.confidence_display = {}

    def set_brush_state(self, is_positive: bool) -> str:
        """
        Sets the brush context. Positive strokes (green) add to the mask,
        Negative strokes (red) subtract.
        """
        self.stroke_type = "positive" if is_positive else "negative"
        return "green" if is_positive else "red"

    def apply_stroke(self, stroke_data: Any) -> Dict[str, str]:
        """
        Simulates the user releasing the mouse to apply a stroke.
        Instantly provides visual feedback while the AI processes in the background.
        """
        self.processing_state = "processing"
        
        # In a real UI, this triggers a "processing spinner" or a pulsed glow on the stroke.
        return {
            "ui_feedback": "pulsing_stroke_glow",
            "state": self.processing_state,
            "minimizing_delay": True # Signals to not block the main thread
        }

    def complete_processing_transition(self) -> str:
        """
        Simulates the AI finishing its SAM calculation and smoothly blending
        the user's raw paint stroke into the final high-res mask overlay.
        """
        self.processing_state = "transitioning"
        # In UI, triggers a 0.2s crossfade animation
        self.processing_state = "idle"
        return "smooth_crossfade_to_mask"

    def update_confidence_display(self, score: float, edge_status: str, tracking: str):
        """
        Updates the on-screen heads-up display (HUD) with real-time mask metrics.
        """
        self.confidence_display = {
            "score_percent": round(score, 1),
            "edge_quality": edge_status,
            "tracking_status": tracking
        }
        
    def get_hud_data(self) -> Dict[str, Any]:
        return self.confidence_display
