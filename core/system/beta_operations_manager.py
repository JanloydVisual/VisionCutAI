from typing import Dict, Any, List

class BetaOperationsManager:
    """
    Infrastructure for version tracking, update management, beta tester
    profiles, and automated release notes generation.
    """
    def __init__(self):
        self.current_version = "1.0.0-beta.1"
        self.testers: Dict[str, Dict[str, Any]] = {}
        self.release_log: List[Dict[str, Any]] = []

    # ── 1. Version Tracking ────────────────────────────────────────────

    def get_version_info(self) -> Dict[str, str]:
        return {
            "app_version": self.current_version,
            "min_compatible_project_version": "1.0.0-beta.1",
            "api_version": "1"
        }

    def is_project_compatible(self, project_version: str) -> bool:
        return project_version >= self.get_version_info()["min_compatible_project_version"]

    # ── 2. Update Management ───────────────────────────────────────────

    def check_for_update(self, latest_available: str) -> Dict[str, Any]:
        needs_update = latest_available > self.current_version
        return {
            "current": self.current_version,
            "latest": latest_available,
            "update_available": needs_update
        }

    def perform_update(self, new_version: str) -> Dict[str, str]:
        """Mock update: backup → apply → verify."""
        backup_status = "BACKUP_CREATED"
        self.current_version = new_version
        verify_status = "VERIFIED"
        return {
            "backup": backup_status,
            "applied_version": new_version,
            "post_update_verify": verify_status
        }

    # ── 3. Beta Tester Management ──────────────────────────────────────

    def register_tester(self, tester_id: str, hardware: Dict[str, Any]):
        self.testers[tester_id] = {
            "hardware": hardware,
            "feedback_history": [],
            "version": self.current_version
        }

    def log_tester_feedback(self, tester_id: str, feedback: str):
        if tester_id in self.testers:
            self.testers[tester_id]["feedback_history"].append(feedback)

    def get_tester_profile(self, tester_id: str) -> Dict[str, Any]:
        return self.testers.get(tester_id, {})

    # ── 4. Release Notes Generator ─────────────────────────────────────

    def add_release_entry(self, version: str, changes: List[str],
                          fixes: List[str], improvements: List[str]):
        self.release_log.append({
            "version": version,
            "changes": changes,
            "fixes": fixes,
            "improvements": improvements
        })

    def generate_release_notes(self, version: str) -> str:
        for entry in self.release_log:
            if entry["version"] == version:
                lines = [f"# VisionCut AI {version} Release Notes\n"]
                if entry["changes"]:
                    lines.append("## Changes")
                    lines.extend(f"- {c}" for c in entry["changes"])
                if entry["fixes"]:
                    lines.append("\n## Fixes")
                    lines.extend(f"- {f}" for f in entry["fixes"])
                if entry["improvements"]:
                    lines.append("\n## Improvements")
                    lines.extend(f"- {i}" for i in entry["improvements"])
                return "\n".join(lines)
        return ""
