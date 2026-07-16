
import json
import sys
from pathlib import Path
from datetime import datetime


def _get_app_data_dir() -> Path:
    """Get application data directory - executable folder or project root."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


class AutoSaveManager:

    def __init__(self):
        self.folder = _get_app_data_dir() / "autosave"
        self.folder.mkdir(parents=True, exist_ok=True)

        self.file = self.folder / "recovery.json"

    def save(self, project):
        data = {
            "project_name": project.name,
            "saved_at": datetime.now().isoformat(),
            "timeline": project.timeline.snapshot(),
        }

        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        project.modified = False

    def exists(self):
        return self.file.exists()

    def load_data(self):
        if not self.exists():
            return None

        with open(self.file, "r", encoding="utf-8") as f:
            return json.load(f)
