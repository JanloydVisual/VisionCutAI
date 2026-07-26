from typing import Dict, Any, List
import numpy as np

class WorkflowOptimizer:
    """
    Analyzes footage characteristics to auto-detect workflow type and apply
    targeted AI quality optimizations based on P54 beta simulation findings.
    """
    def __init__(self):
        self.correction_log: List[Dict[str, Any]] = []

    # ── 1. Workflow Detection ──────────────────────────────────────────

    def detect_workflow(self, avg_motion: float, object_count: int,
                        edge_complexity: float) -> str:
        """
        Classifies footage into one of the three production categories
        based on optical-flow magnitude, object count, and edge detail score.
        """
        if avg_motion > 8.0 and object_count >= 2:
            return "Real Estate"
        elif edge_complexity > 0.7 and object_count <= 1:
            return "Product"
        else:
            return "Talking Head"

    # ── 2. Real Estate Optimizations ───────────────────────────────────

    def optimize_reanchor_timing(self, motion_magnitude: float,
                                  current_interval: int) -> int:
        """
        Dynamically adjusts the re-anchor interval based on motion intensity.
        High-motion Real Estate footage gets more frequent re-anchors to
        prevent mask drift, directly addressing the P54 friction finding
        (12 refinement clicks → target ≤4).
        """
        if motion_magnitude > 15.0:
            return max(5, current_interval // 4)   # Very aggressive
        elif motion_magnitude > 8.0:
            return max(10, current_interval // 2)  # Moderate
        return current_interval                     # No change needed

    def compute_motion_confidence_boost(self, motion_magnitude: float) -> float:
        """
        Returns a multiplier that compensates for the confidence penalty
        applied by MotionRecoveryEngine on high-motion frames.  For Real
        Estate footage this prevents premature mask abandonment.
        """
        if motion_magnitude > 12.0:
            return 1.25   # Boost confidence by 25 %
        elif motion_magnitude > 8.0:
            return 1.10
        return 1.0

    # ── 3. Correction Analytics ────────────────────────────────────────

    def log_correction(self, frame: int, correction_type: str,
                       region: str):
        """Records every manual refinement so we can mine patterns later."""
        self.correction_log.append({
            "frame": frame,
            "type": correction_type,   # "positive" | "negative"
            "region": region            # e.g. "edge_left", "top_right"
        })

    def generate_quality_insights(self) -> Dict[str, Any]:
        """
        Analyses the accumulated correction log to surface recurring
        patterns the AI consistently gets wrong.
        """
        total = len(self.correction_log)
        if total == 0:
            return {"total_corrections": 0, "top_region": "N/A",
                    "positive_ratio": 0.0}

        region_counts: Dict[str, int] = {}
        positive_count = 0
        for c in self.correction_log:
            r = c["region"]
            region_counts[r] = region_counts.get(r, 0) + 1
            if c["type"] == "positive":
                positive_count += 1

        top_region = max(region_counts, key=region_counts.get)
        return {
            "total_corrections": total,
            "top_region": top_region,
            "positive_ratio": positive_count / total,
            "region_breakdown": region_counts
        }

    # ── 4. Workflow Success Scoring ────────────────────────────────────

    def compute_success_score(self, time_to_first_mask_sec: float,
                              refinement_clicks: int,
                              export_success: bool,
                              tracking_failures: int) -> Dict[str, Any]:
        """
        Produces a 0-100 score representing how smoothly the workflow
        completed.  Higher is better.
        """
        score = 100.0

        # Penalise slow first-mask times (target < 5 s)
        if time_to_first_mask_sec > 10.0:
            score -= 20.0
        elif time_to_first_mask_sec > 5.0:
            score -= 10.0

        # Penalise excessive refinement (target ≤ 4 clicks)
        excess = max(0, refinement_clicks - 4)
        score -= excess * 3.0

        # Penalise tracking failures
        score -= tracking_failures * 5.0

        # Export failure is a hard penalty
        if not export_success:
            score -= 25.0

        score = max(0.0, min(100.0, score))

        tier = ("Excellent" if score >= 90 else
                "Good" if score >= 70 else
                "Needs Improvement" if score >= 50 else
                "Poor")

        return {"score": round(score, 1), "tier": tier}
