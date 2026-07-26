from datetime import datetime
from typing import List, Dict, Any

class AIEventLogger:
    """
    Records and surfaces AI decisions (reanchors, failures, cache ops) to the UI.
    """
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        
    def log_event(self, event_type: str, message: str):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message
        }
        self.events.append(event)
        
    def get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        return self.events[-count:]
