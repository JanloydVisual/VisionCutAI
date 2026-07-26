from typing import Dict, Any, List

class BetaFeedbackIntelligence:
    """
    Collects, ranks, and analyzes beta user feedback to prioritize
    post-beta improvements without touching the AI pipeline.
    """
    def __init__(self):
        self.feedback_entries: List[Dict[str, Any]] = []
        self.hardware_reports: List[Dict[str, Any]] = []

    # ── 1. Feedback Collection ─────────────────────────────────────────

    def submit_feedback(self, user_id: str, category: str, description: str,
                        severity: int, hardware_info: Dict[str, Any] = None):
        """
        Records a single piece of beta feedback.
        severity: 1 (cosmetic) → 5 (data-loss / crash)
        """
        entry = {
            "user_id": user_id,
            "category": category,
            "description": description,
            "severity": severity,
            "status": "NEW"
        }
        self.feedback_entries.append(entry)

        if hardware_info:
            self.hardware_reports.append({
                "user_id": user_id,
                "gpu": hardware_info.get("gpu", "Unknown"),
                "vram_mb": hardware_info.get("vram_mb", 0),
                "os": hardware_info.get("os", "Unknown"),
                "issue_linked": len(self.feedback_entries) - 1
            })

    # ── 2. Bug Severity Ranking ────────────────────────────────────────

    def get_ranked_bugs(self) -> List[Dict[str, Any]]:
        """Returns all feedback sorted by severity (highest first)."""
        return sorted(self.feedback_entries, key=lambda e: e["severity"], reverse=True)

    # ── 3. Hardware Compatibility Reports ──────────────────────────────

    def get_hardware_compatibility_summary(self) -> Dict[str, Any]:
        """Aggregates hardware data to find problem GPU models."""
        gpu_counts: Dict[str, int] = {}
        for r in self.hardware_reports:
            gpu = r["gpu"]
            gpu_counts[gpu] = gpu_counts.get(gpu, 0) + 1

        return {
            "total_reports": len(self.hardware_reports),
            "gpu_issue_distribution": gpu_counts
        }

    # ── 4. Workflow Success Analytics ──────────────────────────────────

    def compute_workflow_success_rate(self) -> Dict[str, Any]:
        """Calculates how many feedback entries are non-blocking vs critical."""
        if not self.feedback_entries:
            return {"total": 0, "success_rate": 100.0}

        blocking = sum(1 for e in self.feedback_entries if e["severity"] >= 4)
        total = len(self.feedback_entries)
        return {
            "total": total,
            "blocking_issues": blocking,
            "success_rate": round((1 - blocking / total) * 100, 1)
        }

    # ── 5. Beta Improvement Dashboard ──────────────────────────────────

    def get_dashboard(self) -> Dict[str, Any]:
        """Single-call summary for the developer dashboard UI."""
        ranked = self.get_ranked_bugs()
        top_issues = ranked[:5] if ranked else []
        return {
            "total_feedback": len(self.feedback_entries),
            "top_5_issues": top_issues,
            "hardware_summary": self.get_hardware_compatibility_summary(),
            "workflow_analytics": self.compute_workflow_success_rate()
        }
