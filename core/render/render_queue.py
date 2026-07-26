from core.project.project import Project
from core.timeline.clip import Clip
from typing import List, Optional
import time

class RenderQueueManager:
    """
    Foundation for the rendering queue and batch export system.
    """
    def __init__(self, project: Project):
        self.project = project
        self.queue = []
        self.is_rendering = False

    def add_to_queue(self, clip: Clip, settings: dict = None):
        if settings is None:
            settings = {}
        self.queue.append({
            "clip": clip,
            "settings": settings,
            "status": "pending",
            "added_at": time.time()
        })

    def remove_from_queue(self, index: int):
        if 0 <= index < len(self.queue):
            self.queue.pop(index)

    def start_render(self):
        self.is_rendering = True
        for item in self.queue:
            if item["status"] == "pending":
                item["status"] = "processing"
                # Mock render process
                time.sleep(0.1)
                item["status"] = "completed"
        self.is_rendering = False

    def get_queue_status(self) -> List[dict]:
        return self.queue
