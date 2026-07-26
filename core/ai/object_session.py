from core.ai.anchor_manager import AnchorManager
from typing import Dict, Any, Optional

class ObjectSession:
    """
    Encapsulates state for a single independent tracked object in the video.
    Allows VisionCut AI to support multiple layered masks.
    """
    def __init__(self, object_id: str, object_name: str = "Object 1", z_index: int = 0):
        self.object_id = object_id
        self.object_name = object_name
        self.display_name = object_name
        self.visible = True
        self.locked = False
        self.z_index = z_index
        self.anchor_manager = AnchorManager()
        self.tracking_state: Dict[int, Any] = {}
        self.refinement_history: list = []
        
        self.prompt_history: list = []
        self.undo_stack: list = []
        self.redo_stack: list = []
        
        # Mask Cache namespace string (e.g. "object_001")
        self.cache_namespace = f"object_{self.object_id}"
        
    def reset(self):
        self.anchor_manager.clear()
        self.tracking_state.clear()
        self.refinement_history.clear()
