from typing import Dict, Any, List
import time

class BetaExperienceAnalytics:
    """
    Aggregates user journey data, feature usage, and drop-off patterns
    to surface actionable UX optimizations from real beta telemetry.
    """
    def __init__(self):
        self.journeys: List[Dict[str, Any]] = []
        self.feature_usage: Dict[str, int] = {}

    # ── 1. User Journey Analytics ──────────────────────────────────────

    def start_journey(self, user_id: str) -> int:
        """Creates a new journey record and returns its index."""
        self.journeys.append({
            "user_id": user_id,
            "stages": {},
            "start_time": time.time(),
            "completed": False
        })
        return len(self.journeys) - 1

    def record_stage(self, journey_idx: int, stage: str):
        """Marks a workflow stage as reached (startup/import/first_mask/tracking/export)."""
        if 0 <= journey_idx < len(self.journeys):
            self.journeys[journey_idx]["stages"][stage] = time.time()
            if stage == "export":
                self.journeys[journey_idx]["completed"] = True

    # ── 2. Feature Usage Analytics ─────────────────────────────────────

    def log_feature_use(self, feature: str):
        self.feature_usage[feature] = self.feature_usage.get(feature, 0) + 1

    def get_feature_usage_report(self) -> Dict[str, int]:
        return dict(sorted(self.feature_usage.items(), key=lambda x: x[1], reverse=True))

    # ── 3. Workflow Drop-off Detection ─────────────────────────────────

    def detect_dropoffs(self) -> Dict[str, Any]:
        """Identifies where users abandon the workflow."""
        stage_order = ["startup", "import", "first_mask", "tracking", "export"]
        dropoff_counts: Dict[str, int] = {s: 0 for s in stage_order}
        incomplete = 0

        for j in self.journeys:
            if j["completed"]:
                continue
            incomplete += 1
            last_reached = "startup"
            for s in stage_order:
                if s in j["stages"]:
                    last_reached = s
            dropoff_counts[last_reached] += 1

        return {
            "incomplete_projects": incomplete,
            "dropoff_by_stage": dropoff_counts
        }

    # ── 4. Beta Health Dashboard ───────────────────────────────────────

    def get_health_dashboard(self) -> Dict[str, Any]:
        total = len(self.journeys)
        completed = sum(1 for j in self.journeys if j["completed"])
        completion_rate = (completed / total * 100) if total else 0.0

        durations = []
        for j in self.journeys:
            if j["completed"] and "export" in j["stages"]:
                durations.append(j["stages"]["export"] - j["start_time"])
        avg_time = sum(durations) / len(durations) if durations else 0.0

        return {
            "total_journeys": total,
            "completion_rate_percent": round(completion_rate, 1),
            "avg_workflow_time_sec": round(avg_time, 2),
            "export_success_count": completed,
            "feature_popularity": self.get_feature_usage_report(),
            "dropoff_analysis": self.detect_dropoffs()
        }
