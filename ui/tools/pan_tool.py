from PyQt6.QtCore import Qt
from ui.tools.base_tool import BaseToolState

class PanToolState(BaseToolState):
    """
    Global tool that intercepts middle-mouse button for panning.
    """
    def __init__(self):
        super().__init__()
        self._is_panning = False
        self._pan_start = None

    def cancel(self) -> None:
        if self._is_panning:
            self._is_panning = False
            self._pan_start = None
            if self.viewer:
                self.viewer.setCursor(Qt.CursorShape.ArrowCursor)

    def on_mouse_press(self, event) -> bool:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.viewer.setCursor(Qt.CursorShape.ClosedHandCursor)
            return True
        return False

    def on_mouse_move(self, event) -> bool:
        if self._is_panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            
            # Pan the view
            h_bar = self.viewer.horizontalScrollBar()
            v_bar = self.viewer.verticalScrollBar()
            h_bar.setValue(int(h_bar.value() - delta.x()))
            v_bar.setValue(int(v_bar.value() - delta.y()))
            
            self._pan_start = event.position()
            return True
        return False

    def on_mouse_release(self, event) -> bool:
        if event.button() == Qt.MouseButton.MiddleButton and self._is_panning:
            self._is_panning = False
            self._pan_start = None
            self.viewer.setCursor(Qt.CursorShape.ArrowCursor)
            return True
        return False
