from PyQt6.QtCore import Qt
from ui.tools.base_tool import BaseToolState

class PointToolState(BaseToolState):
    """
    Point tool for precision interaction.
    - Left mouse button -> positive point (label=1)
    - Right mouse button -> negative point (label=0)
    """
    def activate(self, viewer) -> None:
        super().activate(viewer)
        self.viewer.setCursor(Qt.CursorShape.CrossCursor)

    def deactivate(self) -> None:
        self.cancel()
        if self.viewer:
            self.viewer.setCursor(Qt.CursorShape.ArrowCursor)
        super().deactivate()

    def on_mouse_press(self, event) -> bool:
        if not self.viewer:
            return False

        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            scene_pos = self.viewer.mapToScene(event.position().toPoint())
            px = scene_pos.x()
            py = scene_pos.y()
            
            # Label: 1 for left click, 0 for right click (ignoring old _mask_mode logic per new spec)
            label = 1 if event.button() == Qt.MouseButton.LeftButton else 0
            
            # Emit the point immediately on click
            self.viewer.target_object_selected.emit({
                'type': 'point',
                'data': [px, py],
                'label': label
            })
            return True
            
        return False
