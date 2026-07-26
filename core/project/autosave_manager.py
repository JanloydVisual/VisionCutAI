import os
import json
from datetime import datetime

class AutosaveManager:
    """
    Handles automatic state serialization and crash recovery detection.
    """
    def __init__(self, backup_dir: str = "project_cache/autosave"):
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def save_state(self, project_data: dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.backup_dir, f"autosave_{timestamp}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(project_data, f)
        return filepath
        
    def check_for_recovery(self) -> str:
        # Returns latest autosave path if one exists
        if not os.path.exists(self.backup_dir):
            return ""
        files = [f for f in os.listdir(self.backup_dir) if f.startswith("autosave_")]
        if not files:
            return ""
        files.sort(reverse=True)
        return os.path.join(self.backup_dir, files[0])
