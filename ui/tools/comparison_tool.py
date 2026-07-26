from PyQt6.QtCore import Qt, QRectF
from ui.tools.base_tool import BaseToolState

class ComparisonToolState(BaseToolState):
    """
    Global tool that intercepts left-mouse drags near the divider line
    when the viewer is in 'split' mode.
    """
    HANDLE_HIT_TOLERANCE = 10

    def __init__(self):
        super().__init__()
        self._is_dragging = False

    def cancel(self) -> None:
        if self._is_dragging:
            self._is_dragging = False
            if self.viewer:
                self.viewer.setCursor(Qt.CursorShape.ArrowCursor)

    def on_mouse_press(self, event) -> bool:
        if not self.viewer or self.viewer._preview_mode != "split":
            return False

        if event.button() == Qt.MouseButton.LeftButton:
            x = self.viewer._divider_viewport_x()
            if x is not None:
                hit_rect = QRectF(x - self.HANDLE_HIT_TOLERANCE, 0, self.HANDLE_HIT_TOLERANCE * 2, self.viewer.viewport().height())
                if hit_rect.contains(event.position()):
                    self.viewer.setCursor(Qt.CursorShape.SizeHorCursor)
                    self._is_dragging = True
                    return True
        return False

    def on_mouse_move(self, event) -> bool:
        if self._is_dragging and self.viewer and self.viewer._last_frame_size is not None:
            scene_pos = self.viewer.mapToScene(event.position().toPoint())
            fraction = scene_pos.x() / self.viewer._last_frame_size.width()
            self.viewer._set_comparison_fraction(fraction)
            return True
        return False

    def on_mouse_release(self, event) -> bool:
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            self.viewer.setCursor(Qt.CursorShape.ArrowCursor)
            return True
        return False
