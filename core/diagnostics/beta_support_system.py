from typing import Dict, Any, List

class BetaSupportSystem:
    """
    Professional support workflow for external beta users: feedback center,
    diagnostic packaging, tutorial improvement signals, and a support dashboard.
    """
    def __init__(self):
        self.tickets: List[Dict[str, Any]] = []
        self.tester_status: Dict[str, str] = {}

    # ── 1. In-App Feedback Center ──────────────────────────────────────

    def submit_ticket(self, user_id: str, category: str, description: str,
                      severity: int, attachments: List[str] = None) -> int:
        ticket = {
            "id": len(self.tickets),
            "user_id": user_id,
            "category": category,
            "description": description,
            "severity": severity,
            "attachments": attachments or [],
            "status": "OPEN"
        }
        self.tickets.append(ticket)
        self.tester_status[user_id] = "ACTIVE"
        return ticket["id"]

    def resolve_ticket(self, ticket_id: int, resolution: str):
        if 0 <= ticket_id < len(self.tickets):
            self.tickets[ticket_id]["status"] = "RESOLVED"
            self.tickets[ticket_id]["resolution"] = resolution

    # ── 2. Automatic Diagnostic Package ────────────────────────────────

    def generate_diagnostic_package(self, user_id: str) -> Dict[str, Any]:
        user_tickets = [t for t in self.tickets if t["user_id"] == user_id]
        return {
            "user_id": user_id,
            "logs": ["app.log", "crash.log"],
            "hardware_info": {"gpu": "NVIDIA RTX series", "vram_mb": 8192, "os": "Windows 11"},
            "project_diagnostics": {"open_projects": 1, "cache_healthy": True},
            "workflow_history_entries": len(user_tickets),
            "recent_tickets": user_tickets[-3:]
        }

    # ── 3. Tutorial Improvement Connection ─────────────────────────────

    def identify_confusing_steps(self, dropoff_data: Dict[str, Any]) -> List[Dict[str, str]]:
        suggestions = []
        stages = dropoff_data.get("dropoff_by_stage", {})
        for stage, count in stages.items():
            if count > 0:
                suggestions.append({
                    "stage": stage,
                    "dropoff_count": count,
                    "suggestion": f"Improve onboarding guidance for '{stage}' step."
                })
        return sorted(suggestions, key=lambda s: s["dropoff_count"], reverse=True)

    # ── 4. Beta User Support Dashboard ─────────────────────────────────

    def get_support_dashboard(self) -> Dict[str, Any]:
        open_count = sum(1 for t in self.tickets if t["status"] == "OPEN")
        resolved_count = sum(1 for t in self.tickets if t["status"] == "RESOLVED")
        return {
            "total_tickets": len(self.tickets),
            "open": open_count,
            "resolved": resolved_count,
            "resolution_rate_percent": round(resolved_count / len(self.tickets) * 100, 1) if self.tickets else 0.0,
            "active_testers": len(self.tester_status),
            "top_category": self._top_category()
        }

    def _top_category(self) -> str:
        cats: Dict[str, int] = {}
        for t in self.tickets:
            cats[t["category"]] = cats.get(t["category"], 0) + 1
        return max(cats, key=cats.get) if cats else "N/A"
