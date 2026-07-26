from typing import Dict, Any, List

class ProductionControlCenter:
    """
    A unified production management view providing a holistic overview of
    batch workflows, smart retries, and comprehensive project history.
    """
    def __init__(self, batch_manager=None, project_library=None):
        self.batch_manager = batch_manager
        self.project_library = project_library
        self.production_history = []

    def get_master_dashboard_metrics(self) -> Dict[str, Any]:
        """Provides high-level metrics for the entire production workload."""
        # Mocking data that would normally be aggregated from batch_manager
        return {
            "total_clips": 150,
            "completion_status_percent": 85.0,
            "global_quality_score": 92.5,
            "clips_pending_review": 4
        }

    def generate_batch_review_queue(self) -> List[Dict[str, Any]]:
        """
        Prioritizes problematic clips from a batch run so a human editor
        can jump directly to the most critical failures.
        """
        # Mock prioritized list
        return [
            {"clip_id": "clip_42", "reason": "CRITICAL_TRACKING_LOSS", "priority": 1},
            {"clip_id": "clip_89", "reason": "HIGH_EDGE_COMPLEXITY", "priority": 2},
            {"clip_id": "clip_12", "reason": "UNRESOLVED_WARNINGS", "priority": 3}
        ]

    def smart_retry_clip(self, clip_id: str, failure_reason: str) -> Dict[str, Any]:
        """
        Analyzes a specific clip failure and automatically suggests
        or applies recovery settings (e.g. degrading to FAST mode, forcing re-anchors).
        """
        suggestion = "Apply default settings."
        if "VRAM_EXHAUSTED" in failure_reason:
            suggestion = "Degrade to FAST preview mode and clear cache."
        elif "TRACKING_LOSS" in failure_reason:
            suggestion = "Increase re-anchor frequency to 10 frames."
            
        return {
            "clip_id": clip_id,
            "applied_recovery_settings": suggestion,
            "retry_status": "QUEUED"
        }

    def log_production_history(self, batch_stats: Dict[str, Any]):
        """Persistently records processing stats and export records."""
        self.production_history.append(batch_stats)
        
    def get_production_history(self) -> List[Dict[str, Any]]:
        return self.production_history
