"""
ViewerWidget
------------
QGraphicsView-based zoomable, pannable video viewer.
Owns zoom/pan state only. No knowledge of VideoEngine/Controller.
"""

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QWheelEvent, QMouseEvent


class ViewerWidget(QGraphicsView):

    zoom_changed = pyqtSignal(float)

    MIN_ZOOM = 0.05
    MAX_ZOOM = 20.0
    ZOOM_STEP = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)

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

    # ---------------- Frame updates ----------------

    def load_frame(self, pixmap: QPixmap) -> None:
        if pixmap is None or pixmap.isNull():
            return

        new_size = pixmap.size()
        first_frame = self._last_frame_size is None
        size_changed = new_size != self._last_frame_size

        self._pixmap_item.setPixmap(pixmap)

        if size_changed:
            self._scene.setSceneRect(QRectF(0, 0, new_size.width(), new_size.height()))
            self._last_frame_size = new_size
            if first_frame:
                self.fit_to_window()

    def clear(self) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._last_frame_size = None
        self._zoom_factor = 1.0
        self.resetTransform()

    # ---------------- Zoom ----------------

    def fit_to_window(self) -> None:
        if self._pixmap_item.pixmap().isNull():
            return
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_factor = self.transform().m11()
        self.zoom_changed.emit(self._zoom_factor)

    def set_zoom(self, factor: float) -> None:
        if self._pixmap_item.pixmap().isNull():
            return
        factor = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
        self.resetTransform()
        self.scale(factor, factor)
        self._zoom_factor = factor
        self.centerOn(self._pixmap_item)
        self.zoom_changed.emit(self._zoom_factor)

    def zoom_100(self) -> None:
        self.set_zoom(1.0)

    def zoom_200(self) -> None:
        self.set_zoom(2.0)

    def reset_view(self) -> None:
        self.fit_to_window()

    def _apply_zoom_step(self, angle_delta: int) -> None:
        if self._pixmap_item.pixmap().isNull():
            return
        step = self.ZOOM_STEP if angle_delta > 0 else (1 / self.ZOOM_STEP)
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom_factor * step))
        if new_zoom == self._zoom_factor:
            return
        ratio = new_zoom / self._zoom_factor
        self.scale(ratio, ratio)
        self._zoom_factor = new_zoom
        self.zoom_changed.emit(self._zoom_factor)

    # ---------------- Mouse events (zoom + middle-button pan) ----------------

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
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
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
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
