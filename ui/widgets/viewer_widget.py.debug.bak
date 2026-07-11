"""
ViewerWidget
------------
QGraphicsView-based zoomable, pannable video viewer with:
    - checkerboard background (visible through transparent pixels)
    - original/processed pixmap layers
    - draggable original<->processed comparison slider

Owns viewer/render state only. No knowledge of VideoEngine/Controller.
"""

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QWheelEvent, QMouseEvent


class _CheckerboardScene(QGraphicsScene):
    """Scene background: tiled checkerboard, clipped to sceneRect.
    Shows through wherever items above it are transparent/absent."""

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
    """Pixmap item that only paints the region right of a fraction
    (0..1) of its own width, letting whatever is beneath show
    through on the left. Used for the comparison slider - no pixmap
    copying, just a clip rect recomputed at paint time."""

    def __init__(self):
        super().__init__()
        self._clip_fraction = 0.5

    def set_clip_fraction(self, fraction: float) -> None:
        self._clip_fraction = max(0.0, min(1.0, fraction))
        self.update()

    def paint(self, painter, option, widget=None):
        pixmap = self.pixmap()
        if pixmap.isNull():
            return

        rect = self.boundingRect()
        clip_x = rect.width() * self._clip_fraction
        clip_rect = QRectF(
            rect.left() + clip_x, rect.top(),
            rect.width() - clip_x, rect.height()
        )

        painter.save()
        painter.setClipRect(clip_rect)
        painter.drawPixmap(rect.topLeft(), pixmap)
        painter.restore()


class ViewerWidget(QGraphicsView):

    zoom_changed = pyqtSignal(float)
    comparison_changed = pyqtSignal(float)

    MIN_ZOOM = 0.05
    MAX_ZOOM = 20.0
    ZOOM_STEP = 1.15
    HANDLE_HIT_TOLERANCE = 10

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = _CheckerboardScene(self)
        self.setScene(self._scene)

        self._original_item = QGraphicsPixmapItem()
        self._original_item.setZValue(0)
        self._scene.addItem(self._original_item)

        self._processed_item = _ClippedPixmapItem()
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

    # ---------------- Frame updates ----------------

    def load_frame(self, pixmap: QPixmap) -> None:
        """Sets the original frame. Also mirrors to the processed
        layer until an AI engine calls set_processed_frame()
        explicitly, so the comparison slider is always functional."""
        if pixmap is None or pixmap.isNull():
            return

        new_size = pixmap.size()
        first_frame = self._last_frame_size is None
        size_changed = new_size != self._last_frame_size

        self._original_item.setPixmap(pixmap)
        self._processed_item.setPixmap(pixmap)

        if size_changed:
            self._scene.setSceneRect(QRectF(0, 0, new_size.width(), new_size.height()))
            self._last_frame_size = new_size
            if first_frame:
                self.fit_to_window()

        self._processed_item.set_clip_fraction(self._comparison_fraction)

    def set_processed_frame(self, pixmap: QPixmap) -> None:
        """Hook for the future AI engine: sets only the processed
        (right-hand) layer, independent of the original frame."""
        if pixmap is None or pixmap.isNull():
            return
        self._processed_item.setPixmap(pixmap)
        self._processed_item.set_clip_fraction(self._comparison_fraction)

    def clear(self) -> None:
        self._original_item.setPixmap(QPixmap())
        self._processed_item.setPixmap(QPixmap())
        self._last_frame_size = None
        self._zoom_factor = 1.0
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

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            divider_x = self._divider_viewport_x()
            if divider_x is not None and abs(event.position().x() - divider_x) <= self.HANDLE_HIT_TOLERANCE:
                self._comparison_dragging = True
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._comparison_dragging and self._last_frame_size is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            fraction = scene_pos.x() / self._last_frame_size.width()
            self._set_comparison_fraction(fraction)
            event.accept()
            return

        if self._panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - int(delta.x()))
            v_bar.setValue(v_bar.value() - int(delta.y()))
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._comparison_dragging:
            self._comparison_dragging = False
            event.accept()
            return

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

        if self._last_frame_size is None:
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
