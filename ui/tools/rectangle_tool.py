from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPen, QBrush
from PyQt6.QtWidgets import QGraphicsRectItem
from ui.tools.base_tool import BaseToolState

class RectangleToolState(BaseToolState):
    def __init__(self):
        super().__init__()
        self._is_drawing = False
        self._box_start_scene = None
        self._box_start_logical = None
        self._temp_box_item = None

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
            if self._temp_box_item and self.viewer:
                self.viewer.remove_temp_item(self._temp_box_item)
            self._temp_box_item = None

    def on_mouse_press(self, event) -> bool:
        if not self.viewer: return False
        
        # Right click cancels the current box
        if self._is_drawing and event.button() == Qt.MouseButton.RightButton:
            self.cancel()
            return True
            
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.viewer.mapToScene(event.position().toPoint())
            self._is_drawing = True
            self._box_start_scene = scene_pos
            self._box_start_logical = [scene_pos.x(), scene_pos.y()]
            
            self._temp_box_item = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
            pen = QPen(QColor(40, 210, 80), 2)
            pen.setCosmetic(True)
            self._temp_box_item.setPen(pen)
            self._temp_box_item.setBrush(QBrush(QColor(40, 210, 80, 50)))
            self._temp_box_item.setZValue(15)
            self.viewer.add_temp_item(self._temp_box_item)
            
            return True
            
        return False

    def on_mouse_move(self, event) -> bool:
        if self._is_drawing and self.viewer:
            scene_pos = self.viewer.mapToScene(event.position().toPoint())
            rect = QRectF(self._box_start_scene, scene_pos).normalized()
            self._temp_box_item.setRect(rect)
            return True
            
        return False

    def on_mouse_release(self, event) -> bool:
        if self._is_drawing and event.button() == Qt.MouseButton.LeftButton:
            self._is_drawing = False
            if self.viewer and self._temp_box_item:
                self.viewer.remove_temp_item(self._temp_box_item)
            self._temp_box_item = None
            
            scene_pos = self.viewer.mapToScene(event.position().toPoint())
            end_logical = [scene_pos.x(), scene_pos.y()]
            
            x1 = min(self._box_start_logical[0], end_logical[0])
            y1 = min(self._box_start_logical[1], end_logical[1])
            x2 = max(self._box_start_logical[0], end_logical[0])
            y2 = max(self._box_start_logical[1], end_logical[1])
            
            # Box mode always acts as Keep (label 1)
            if self.viewer:
                self.viewer.target_object_selected.emit({
                    'type': 'rectangle',
                    'data': [x1, y1, x2, y2],
                    'label': 1
                })
            
            return True
            
        return False
