"""
ViewerWidget
------------
QGraphicsView-based zoomable, pannable video viewer with:
    - checkerboard background (visible through transparent pixels)
    - original/processed pixmap layers
    - draggable original<->processed comparison slider
    - preview mode toggle (original vs AI result)

This class owns viewer/render state only. No knowledge of VideoEngine/Controller.
"""

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QWheelEvent, QMouseEvent


class _CheckerboardScene(QGraphicsScene):
    """Scene background: tiled checkerboard, clipped to sceneRect. Shows through wherever items above it are transparent/absent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tile = self._build_tile()

    def _build_tile(self, square: int = 10) -> QPixmap:
        tile = QPixmap(square * 2, square * 2)
        tile.fill(QColor(205, 205, 205))
        painter = QPainter(tile)
        dark = QColor(150, 150, 150)
        painter.fillRect(0, 0, square, square, dark)
        painter.fillRect(square, square, square, square, dark)
        painter.end()
        return tile

    def drawBackground(self, painter, rect):
        target = rect.intersected(self.sceneRect())
        if target.isEmpty():
            return
        painter.drawTiledPixmap(target, self._tile)


class _ClippedPixmapItem(QGraphicsPixmapItem):
    """Pixmap item that paints either the left or right side of a split. Used for the comparison slider - no pixmap copying, just a clip rect recomputed at paint time."""

    def __init__(self, keep_right=True):
        super().__init__()
        self._clip_fraction = 0.5
        self._keep_right = keep_right

    def set_clip_fraction(self, fraction: float) -> None:
        self._clip_fraction = max(0.0, min(1.0, fraction))
        self.update()

    def paint(self, painter, option, widget=None):
        pixmap = self.pixmap()
        if pixmap.isNull():
            return

        rect = self.boundingRect()
        clip_x = rect.width() * self._clip_fraction
        
        if self._keep_right:
            clip_rect = QRectF(
                rect.left() + clip_x, rect.top(),
                rect.width() - clip_x, rect.height()
            )
        else:
            clip_rect = QRectF(
                rect.left(), rect.top(),
                clip_x, rect.height()
            )

        painter.save()
        painter.setClipRect(clip_rect)
        painter.drawPixmap(rect.topLeft(), pixmap)
        painter.restore()


class ViewerWidget(QGraphicsView):

    zoom_changed = pyqtSignal(float)
    comparison_changed = pyqtSignal(float)
    target_object_selected = pyqtSignal(dict)

    MIN_ZOOM = 0.05
    MAX_ZOOM = 20.0
    ZOOM_STEP = 1.15
    HANDLE_HIT_TOLERANCE = 10

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = _CheckerboardScene(self)
        self.setScene(self._scene)

        self._original_item = _ClippedPixmapItem(keep_right=False)
        self._original_item.setZValue(0)
        self._scene.addItem(self._original_item)

        self._processed_item = _ClippedPixmapItem(keep_right=True)
        self._processed_item.setZValue(1)
        self._scene.addItem(self._processed_item)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setStyleSheet("background-color: black; border: none;")

        self._zoom_factor = 1.0
        self._last_frame_size = None

        self._panning = False
        self._pan_start = None

        self._comparison_fraction = 0.5
        self._comparison_dragging = False
        self._has_processed_frame = False

        # Preview mode: 'original', 'split', 'ai'
        self._preview_mode = "original"

        # Drawing mode for target object selection
        self._drawing_mode = False
        self._draw_start = None
        from PyQt6.QtWidgets import QGraphicsRectItem
        self._rect_item = QGraphicsRectItem()
        self._rect_item.setPen(QPen(QColor(0, 255, 0), 2))
        self._rect_item.setZValue(10)
        self._scene.addItem(self._rect_item)
        self._rect_item.hide()

    # ---------------- Frame updates ----------------

    def set_drawing_mode(self, enabled: bool):
        self._drawing_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
            self._rect_item.hide()
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def load_frame(self, pixmap: QPixmap, scale_factor: float = 1.0) -> None:
        """Sets the original frame. Also mirrors to the processed layer until an AI engine calls set_processed_frame() explicitly, so the comparison slider is always functional."""
        if pixmap is None or pixmap.isNull():
            return

        from PyQt6.QtCore import QSizeF
        logical_size = QSizeF(pixmap.width() / scale_factor, pixmap.height() / scale_factor)

        first_frame = self._last_frame_size is None
        size_changed = self._last_frame_size is None or logical_size != self._last_frame_size

        self._original_item.setPixmap(pixmap)
        self._original_item.setScale(1.0 / scale_factor)
        self._processed_item.setScale(1.0 / scale_factor)

        # Update visibility based on preview mode
        self._update_visibility()

        if size_changed:
            self._scene.setSceneRect(QRectF(0, 0, logical_size.width(), logical_size.height()))
            self._last_frame_size = logical_size
            if first_frame:
                self.fit_to_window()
            else:
                self.set_zoom(self._zoom_factor)

    def set_processed_frame(self, pixmap: QPixmap, scale_factor: float = 1.0) -> None:
        """Sets the processed/AI frame."""
        if pixmap is None or pixmap.isNull():
            return
        self._processed_item.setPixmap(pixmap)
        self._processed_item.setScale(1.0 / scale_factor)
        self._has_processed_frame = True
        self._update_visibility()

    def set_preview_mode(self, mode: str) -> None:
        """Set preview mode ('original', 'split', 'ai')."""
        self._preview_mode = mode
        self._update_visibility()
        self.viewport().update()

    def _update_visibility(self) -> None:
        """Update visibility of original and processed layers based on mode."""
        if self._preview_mode == "ai":
            # Show only processed (AI result)
            self._processed_item.set_clip_fraction(0.0)
            self._original_item.set_clip_fraction(0.0)
        elif self._preview_mode == "original":
            # Show only original
            self._processed_item.set_clip_fraction(1.0)
            self._original_item.set_clip_fraction(1.0)
        else:  # split
            # Use comparison fraction
            self._processed_item.set_clip_fraction(self._comparison_fraction)
            self._original_item.set_clip_fraction(self._comparison_fraction)

    def show_processed_preview(self) -> None:
        """Show full AI result (no original visible)."""
        self._preview_mode = "ai"
        self._update_visibility()

    def show_original_preview(self) -> None:
        """Show original only."""
        self._preview_mode = "original"
        self._update_visibility()
        
    def show_split_preview(self) -> None:
        """Show comparison slider."""
        self._preview_mode = "split"
        self._update_visibility()

    def clear(self) -> None:
        self._original_item.setPixmap(QPixmap())
        self._processed_item.setPixmap(QPixmap())
        self._last_frame_size = None
        self._zoom_factor = 1.0
        self._has_processed_frame = False
        self._preview_mode = False
        self.resetTransform()

    # ---------------- Zoom ----------------

    def fit_to_window(self) -> None:
        if self._original_item.pixmap().isNull():
            return
        self.fitInView(self._original_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_factor = self.transform().m11()
        self.zoom_changed.emit(self._zoom_factor)

    def set_zoom(self, factor: float) -> None:
        if self._original_item.pixmap().isNull():
            return
        factor = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
        self.resetTransform()
        self.scale(factor, factor)
        self._zoom_factor = factor
        self.centerOn(self._original_item)
        self.zoom_changed.emit(self._zoom_factor)

    def zoom_100(self) -> None:
        self.set_zoom(1.0)

    def zoom_200(self) -> None:
        self.set_zoom(2.0)

    def reset_view(self) -> None:
        self.fit_to_window()

    def _apply_zoom_step(self, angle_delta: int) -> None:
        if self._original_item.pixmap().isNull():
            return
        step = self.ZOOM_STEP if angle_delta > 0 else (1 / self.ZOOM_STEP)
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom_factor * step))
        if new_zoom == self._zoom_factor:
            return
        ratio = new_zoom / self._zoom_factor
        self.scale(ratio, ratio)
        self._zoom_factor = new_zoom
        self.zoom_changed.emit(self._zoom_factor)

    # ---------------- Comparison slider ----------------

    def _set_comparison_fraction(self, fraction: float) -> None:
        self._comparison_fraction = max(0.0, min(1.0, fraction))
        self._processed_item.set_clip_fraction(self._comparison_fraction)
        self._original_item.set_clip_fraction(self._comparison_fraction)
        self.comparison_changed.emit(self._comparison_fraction)
        self.viewport().update()

    def _divider_viewport_x(self):
        if self._last_frame_size is None:
            return None
        scene_x = self._last_frame_size.width() * self._comparison_fraction
        scene_point = QPointF(scene_x, self._last_frame_size.height() / 2)
        return self.mapFromScene(scene_point).x()

    # ---------------- Mouse events (zoom / pan / comparison drag) ----------------

    def wheelEvent(self, event: QWheelEvent) -> None:
        self._apply_zoom_step(event.angleDelta().y())
        event.accept()

    def mousePressEvent(self, event) -> None:
        if self._drawing_mode and event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._draw_start = self.mapToScene(event.position().toPoint())
            self._current_stroke = [self._draw_start]
            self._stroke_label = 1 if event.button() == Qt.MouseButton.LeftButton else 0
            
            from PyQt6.QtWidgets import QGraphicsPathItem
            from PyQt6.QtGui import QPainterPath
            self._path_item = QGraphicsPathItem()
            color = QColor(0, 255, 0) if self._stroke_label == 1 else QColor(255, 0, 0)
            self._path_item.setPen(QPen(color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            self._path_item.setZValue(10)
            self._scene.addItem(self._path_item)
            
            self._path = QPainterPath(self._draw_start)
            self._path_item.setPath(self._path)
            event.accept()
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            x = self._divider_viewport_x()
            if x is not None and self._preview_mode == "split":
                if abs(event.position().x() - x) < self.HANDLE_HIT_TOLERANCE:
                    self._comparison_dragging = True
                    event.accept()
                    return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drawing_mode and self._draw_start is not None:
            current_pos = self.mapToScene(event.position().toPoint())
            self._current_stroke.append(current_pos)
            self._path.lineTo(current_pos)
            self._path_item.setPath(self._path)
            event.accept()
            return

        if self._comparison_dragging and self._last_frame_size is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            fraction = scene_pos.x() / self._last_frame_size.width()
            self._set_comparison_fraction(fraction)
            event.accept()
            return

        if self._panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            self._pan_start = event.position()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drawing_mode and event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton) and self._draw_start is not None:
            # We don't hide the path immediately, let the user see it briefly (or it clears on next mode switch)
            # Actually, let's clear it since the mask will show up.
            self._scene.removeItem(self._path_item)
            self._draw_start = None
            
            scale_factor = 1.0 / self._original_item.scale() if self._original_item.scale() > 0 else 1.0
            
            # Subsample points if it's a long stroke
            num_points = len(self._current_stroke)
            sampled_points = []
            
            if num_points <= 3:
                # Just a click
                p = self._current_stroke[0]
                sampled_points.append((int(p.x() * scale_factor), int(p.y() * scale_factor)))
            else:
                # Subsample to max 10 points
                step = max(1, num_points // 10)
                for i in range(0, num_points, step):
                    p = self._current_stroke[i]
                    sampled_points.append((int(p.x() * scale_factor), int(p.y() * scale_factor)))
                    if len(sampled_points) >= 10:
                        break
                        
            self.target_object_selected.emit({
                'type': 'points', 
                'data': sampled_points,
                'label': self._stroke_label
            })
            
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._comparison_dragging = False

        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    # ---------------- Divider overlay paint ----------------

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        if self._last_frame_size is None or self._preview_mode != "split":
            return

        x = self._divider_viewport_x()
        if x is None:
            return

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        height = self.viewport().height()

        pen = QPen(QColor(255, 255, 255, 230))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(int(x), 0, int(x), height)

        painter.setBrush(QColor(255, 255, 255, 230))
        painter.drawEllipse(QPointF(x, height / 2), 8, 8)
        painter.end()