from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainterPath, QColor, QPen
from PyQt6.QtWidgets import QGraphicsPathItem
from ui.tools.base_tool import BaseToolState

class BrushToolState(BaseToolState):
    def __init__(self):
        super().__init__()
        self._is_drawing = False
        self._stroke_points = []
        self._stroke_button = None
        self._stroke_label = 1
        
        self._temp_path = None
        self._temp_stroke_item = None

    def activate(self, viewer) -> None:
        super().activate(viewer)
        self.viewer.setCursor(Qt.CursorShape.CrossCursor)

    def deactivate(self) -> None:
        self.cancel()
        if self.viewer:
            self.viewer.setCursor(Qt.CursorShape.ArrowCursor)
        super().deactivate()

    def cancel(self) -> None:
        if self._is_drawing:
            self._is_drawing = False
            if self._temp_stroke_item and self.viewer:
                self.viewer.remove_temp_item(self._temp_stroke_item)
            self._temp_stroke_item = None
            self._temp_path = None

    def on_mouse_press(self, event) -> bool:
        if not self.viewer: return False
        
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            scene_pos = self.viewer.mapToScene(event.position().toPoint())
            px = scene_pos.x()
            py = scene_pos.y()

            self._is_drawing = True
            self._stroke_points = [[px, py]]
            self._stroke_button = event.button()
            
            mask_mode = getattr(self.viewer, '_mask_mode', 1)
            self._stroke_label = mask_mode if event.button() == Qt.MouseButton.LeftButton else (1 if mask_mode == 0 else 0)
            color = QColor(40, 210, 80) if self._stroke_label == 1 else QColor(255, 50, 50)
            
            self._temp_path = QPainterPath()
            self._temp_path.moveTo(scene_pos.x(), scene_pos.y())
            self._temp_stroke_item = QGraphicsPathItem(self._temp_path)
            
            pen = QPen(color, 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCosmetic(True)
            self._temp_stroke_item.setPen(pen)
            self._temp_stroke_item.setZValue(15)
            self.viewer.add_temp_item(self._temp_stroke_item)
            
            return True
            
        return False

    def on_mouse_move(self, event) -> bool:
        if self._is_drawing and self.viewer:
            scene_pos = self.viewer.mapToScene(event.position().toPoint())
            px = scene_pos.x()
            py = scene_pos.y()

            self._stroke_points.append([px, py])
            self._temp_path.lineTo(scene_pos.x(), scene_pos.y())
            self._temp_stroke_item.setPath(self._temp_path)

            # Removed target_object_live_updated.emit to prevent mask modification while drawing
            return True
            
        return False

    def on_mouse_release(self, event) -> bool:
        if self._is_drawing and event.button() == self._stroke_button:
            self._is_drawing = False
            
            # Keep stroke visible briefly while AI processes
            # Give ownership of the item to the viewer so it can remove it when mask arrives
            if self.viewer and self._temp_stroke_item:
                self.viewer.set_active_stroke_item(self._temp_stroke_item)
            
            self._temp_stroke_item = None
            
            if len(self._stroke_points) > 0 and self.viewer:
                self.viewer.target_object_selected.emit({
                    'type': 'stroke',
                    'data': self._stroke_points,
                    'label': self._stroke_label
                })
            
            return True
            
        return False
