from typing import Dict, Any, List

class VersionManager:
    """
    Manages project versioning, client review exports, and change tracking
    for professional delivery workflows.
    """
    def __init__(self):
        self.versions = {}
        self.current_version = "v1.0"
        self._initialize_version(self.current_version)

    def _initialize_version(self, v_id: str):
        self.versions[v_id] = {
            "changes": [],
            "state": "mock_state_data",
            "review_status": "pending"
        }

    def save_version(self, version_id: str, state_data: Any):
        self.versions[version_id] = {
            "changes": [],
            "state": state_data,
            "review_status": "pending"
        }
        self.current_version = version_id

    def restore_version(self, version_id: str) -> Any:
        if version_id in self.versions:
            self.current_version = version_id
            return self.versions[version_id]["state"]
        return None

    def add_change_note(self, frame: int, note: str, resolved: bool = False):
        if self.current_version in self.versions:
            self.versions[self.current_version]["changes"].append({
                "frame": frame,
                "note": note,
                "resolved": resolved
            })

    def export_client_review(self, version_id: str) -> Dict[str, Any]:
        """
        Generates a summary package containing a preview video pathway,
        project quality metrics, and issue statuses for client delivery.
        """
        v = self.versions.get(version_id, {})
        changes = v.get("changes", [])
        resolved_count = sum(1 for c in changes if c["resolved"])
        total_count = len(changes)
        
        return {
            "preview_video_path": f"/exports/client_review_{version_id}.mp4",
            "quality_summary": f"{resolved_count}/{total_count} issues resolved",
            "issue_status": "APPROVED" if (total_count > 0 and resolved_count == total_count) else "NEEDS_REVIEW"
        }

    def compare_versions(self, version_a: str, version_b: str) -> Dict[str, Any]:
        """
        Compares mask changes and review status between two distinct project versions.
        """
        va = self.versions.get(version_a, {})
        vb = self.versions.get(version_b, {})
        
        return {
            "mask_changes_detected": True, # Mock
            "status_transition": f"{va.get('review_status')} -> {vb.get('review_status')}"
        }
