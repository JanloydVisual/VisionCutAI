from PyQt6.QtCore import Qt
from ui.tools.base_tool import BaseToolState

class ZoomToolState(BaseToolState):
    """
    Global tool that intercepts wheel events for zooming.
    """
    def on_wheel(self, event) -> bool:
        if not self.viewer:
            return False
            
        angle_delta = event.angleDelta().y()
        self.viewer._apply_zoom_step(angle_delta)
        return True
