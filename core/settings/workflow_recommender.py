from core.settings.workflow_presets import WorkflowPreset

class WorkflowRecommender:
    """
    Analyzes video metrics to recommend the optimal WorkflowPreset.
    """
    @staticmethod
    def recommend(duration_sec: int, resolution: str, motion_level: str, object_count: int, previous_type: str = "") -> WorkflowPreset:
        if object_count > 2:
            return WorkflowPreset.REAL_ESTATE
        elif motion_level == "low" and object_count == 1:
            return WorkflowPreset.TALKING_HEAD
        elif resolution in ["4K", "8K"] or motion_level == "high":
            return WorkflowPreset.PRODUCT
        return WorkflowPreset.FAST_PREVIEW
