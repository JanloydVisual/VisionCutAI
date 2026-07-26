from typing import Dict, Any, List

class IntelligentBatchManager:
    """
    Manages high-volume, overnight batch production workflows by combining
    workflow detection with automated preset selection and prioritization.
    """
    def __init__(self, workflow_optimizer=None, quality_predictor=None):
        self.optimizer = workflow_optimizer
        self.predictor = quality_predictor
        self.queue: List[Dict[str, Any]] = []
        self.processing = False
        self.paused = False

    def add_to_queue(self, clip_path: str, motion_magnitude: float, object_count: int, edge_complexity: float):
        """
        Ingests a clip, automatically detects its optimal workflow,
        and estimates processing time based on complexity.
        """
        # Mock detection using P55 optimizer logic
        workflow_type = "Talking Head"
        if self.optimizer:
            workflow_type = self.optimizer.detect_workflow(motion_magnitude, object_count, edge_complexity)
            
        # Priority: Real Estate (high motion) > Product (complex edges) > Talking Head (simple)
        priority = 1
        if workflow_type == "Real Estate":
            priority = 3
        elif workflow_type == "Product":
            priority = 2

        # Mock time estimation
        estimated_time_sec = 60.0 * priority

        self.queue.append({
            "path": clip_path,
            "workflow_type": workflow_type,
            "priority": priority,
            "estimated_time_sec": estimated_time_sec,
            "status": "pending",
            "readiness_score": 0
        })
        
        # Sort queue by priority (highest first)
        self.queue.sort(key=lambda x: x["priority"], reverse=True)

    def process_overnight_mode(self):
        """
        Executes the queue. Designed to run unsupervised.
        Supports pausing and recovery.
        """
        self.processing = True
        self.paused = False
        
        for job in self.queue:
            if self.paused:
                break
                
            if job["status"] == "pending":
                job["status"] = "processing"
                # Mock processing step...
                job["status"] = "completed"
                # Mock Export readiness assignment
                job["readiness_score"] = 95 if job["workflow_type"] == "Talking Head" else 85
                
        if not self.paused:
            self.processing = False

    def pause_queue(self):
        self.paused = True

    def resume_queue(self):
        self.process_overnight_mode()

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Provides holistic metrics for the Batch Dashboard UI."""
        completed = sum(1 for j in self.queue if j["status"] == "completed")
        failed = sum(1 for j in self.queue if j["status"] == "failed")
        pending = sum(1 for j in self.queue if j["status"] == "pending")
        
        avg_readiness = 0
        if completed > 0:
            avg_readiness = sum(j["readiness_score"] for j in self.queue if j["status"] == "completed") / completed

        return {
            "total_clips": len(self.queue),
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "average_export_readiness": round(avg_readiness, 1),
            "is_processing": self.processing,
            "is_paused": self.paused
        }
