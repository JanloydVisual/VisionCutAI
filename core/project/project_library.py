from typing import List, Dict, Any
import os

class ProjectLibrary:
    """
    Manages VisionCut AI project portfolios, disaster recovery, and storage metrics.
    """
    def __init__(self, workspace_path: str = "./visioncut_projects"):
        self.workspace_path = workspace_path
        self.projects = {}
        self.recent_projects = []
        
    def create_project(self, name: str) -> Dict[str, Any]:
        proj_id = f"proj_{len(self.projects)}"
        metadata = {
            "name": name,
            "id": proj_id,
            "created_at": "2026-07-26",
            "size_mb": 0,
            "batch_history": {"completed": [], "failed": []}
        }
        self.projects[proj_id] = metadata
        self._add_to_recent(proj_id)
        return metadata

    def open_project(self, proj_id: str) -> Dict[str, Any]:
        if proj_id in self.projects:
            self._add_to_recent(proj_id)
            return self.projects[proj_id]
        return {}

    def _add_to_recent(self, proj_id: str):
        if proj_id in self.recent_projects:
            self.recent_projects.remove(proj_id)
        self.recent_projects.insert(0, proj_id)
        if len(self.recent_projects) > 10:
            self.recent_projects.pop()

    def get_recent_projects(self) -> List[Dict[str, Any]]:
        return [self.projects[pid] for pid in self.recent_projects]

    def recover_project(self, proj_id: str):
        """Simulates restoring orphaned cache layers and aborted batch states."""
        if proj_id in self.projects:
            # Mock recovery of AI caches
            pass

    def calculate_storage(self, proj_id: str) -> float:
        """Returns mock project size in MB."""
        if proj_id in self.projects:
            size = 1500.0  # Mock 1.5GB
            self.projects[proj_id]["size_mb"] = size
            return size
        return 0.0

    def clear_temporary_cache(self, proj_id: str):
        """Purges volatile tracking frames while preserving hard-rendered masks."""
        if proj_id in self.projects:
            # Mock purge
            self.projects[proj_id]["size_mb"] = 50.0  # Reduced size

    def update_batch_history(self, proj_id: str, completed: List[str], failed: List[str]):
        if proj_id in self.projects:
            self.projects[proj_id]["batch_history"]["completed"].extend(completed)
            self.projects[proj_id]["batch_history"]["failed"].extend(failed)

    def get_batch_statistics(self, proj_id: str) -> Dict[str, Any]:
        if proj_id in self.projects:
            history = self.projects[proj_id]["batch_history"]
            c = len(history["completed"])
            f = len(history["failed"])
            return {
                "completed_count": c,
                "failed_count": f,
                "success_rate": (c / (c + f)) * 100 if (c + f) > 0 else 0
            }
        return {}
