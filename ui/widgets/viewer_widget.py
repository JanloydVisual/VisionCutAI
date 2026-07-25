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

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsItemGroup, QGraphicsItem, QGraphicsRectItem
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QWheelEvent, QMouseEvent, QPainterPath, QBrush


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
    target_object_live_updated = pyqtSignal(dict)

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

        # Initialize mask overlay item (for interactive selection)
        self._mask_overlay_item = QGraphicsPixmapItem()
        self._mask_overlay_item.setZValue(2.0)
        self._scene.addItem(self._mask_overlay_item)
        self._drawing_mode = False
        self._mask_mode = 1

        # Sprint 32B: temporary Developer Debug Overlay -- lets each stage of
        # the interactive segmentation pipeline be inspected independently.
        # All hidden by default; toggled from the Developer Panel.
        self._debug_raw_mask_item = QGraphicsPixmapItem()
        self._debug_raw_mask_item.setZValue(3.0)
        self._debug_raw_mask_item.hide()
        self._scene.addItem(self._debug_raw_mask_item)

        self._debug_cleaned_mask_item = QGraphicsPixmapItem()
        self._debug_cleaned_mask_item.setZValue(3.1)
        self._debug_cleaned_mask_item.hide()
        self._scene.addItem(self._debug_cleaned_mask_item)

        self._debug_points_item = QGraphicsPixmapItem()
        self._debug_points_item.setZValue(3.2)
        self._debug_points_item.hide()
        self._scene.addItem(self._debug_points_item)

        self._debug_layer_visible = {"points": False, "raw_mask": False, "cleaned_mask": False, "final_overlay": True}
        self._last_prompt_points = []  # [(x, y, label), ...] in original-frame coordinates

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

        self._drawing_mode = False
        self._prompt_mode = "stroke"
        self._draw_start = None
        self._path_item = QGraphicsPathItem()
        self._path_item.setZValue(10)
        self._scene.addItem(self._path_item)
        self._path_item.hide()

    # ---------------- Frame updates ----------------

    def set_drawing_mode(self, enabled: bool):
        self._drawing_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_prompt_mode(self, mode: str):
        self._prompt_mode = mode

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
        # _mask_overlay_item is NOT scaled here: its pixmap (built in
        # set_interactive_mask) is always full original-frame resolution --
        # MobileSAM's output gets upsampled back to the source frame's size
        # regardless of preview_scale -- so it already matches the scene's
        # logical coordinate system 1:1. Scaling it by 1/preview_scale here
        # (as this used to) rendered it at up to 4x too large whenever
        # preview quality was below "Full Resolution", pushing most or all
        # of the highlight outside the visible scene -- invisible at the
        # default preview_scale=1.0 only by coincidence (1/1.0 is a no-op).

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

    def reset_view(self) -> None:
        """Reset view to fit the entire image and center the divider."""
        self.fit_to_window()
        self._comparison_fraction = 0.5
        self._update_visibility()
        self.viewport().update()

    def set_interactive_mask(self, mask, is_low_confidence: bool = False):
        if mask is None:
            self._mask_overlay_item.hide()
            self._debug_raw_mask_item.hide()
            self._debug_cleaned_mask_item.hide()
            return

        import numpy as np
        if not isinstance(mask, np.ndarray):
            print("Error: Mask must be a numpy array")
            return

        # Ensure mask is 2D and valid
        if len(mask.shape) != 2:
            print("Error: Mask must be a 2D array")
            return

        h, w = mask.shape
        import cv2
        from PyQt6.QtGui import QImage, QPixmap

        # Debug layer: raw MobileSAM mask, before any post-processing.
        self._set_debug_grayscale_layer(self._debug_raw_mask_item, mask, h, w, (255, 80, 80))

        # 1. Edge cleanup (Morphological closing to remove small holes)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 2. Feathering
        mask_clean = cv2.GaussianBlur(mask_clean, (5, 5), 0)

        # Debug layer: cleaned mask (post morphology + blur), before coloring.
        self._set_debug_grayscale_layer(self._debug_cleaned_mask_item, mask_clean, h, w, (80, 160, 255))

        # Create an RGBA image
        overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # Professional translucent fill + anti-aliased outline. Green means
        # "confident selection"; amber flags a fragmented/uncertain mask
        # (Sprint 31: Confidence Visualization) without interrupting editing
        # with a dialog -- purely a color change on the same overlay.
        if is_low_confidence:
            fill_color = [255, 179, 0, 110]
            outline_color = (255, 179, 0, 255)
        else:
            fill_color = [0, 255, 128, 100]
            outline_color = (0, 255, 128, 255)

        mask_bool = mask_clean > 100
        overlay[mask_bool] = fill_color

        # 3. Outline (Anti-aliased bright edge)
        contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, outline_color, 2, cv2.LINE_AA)

        # Keep a reference to prevent garbage collection!
        self._current_overlay_data = overlay

        # Must explicitly use strides in case of weird alignment, though w*4 is usually fine
        qimg = QImage(overlay.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        pixmap = QPixmap.fromImage(qimg)

        self._mask_overlay_item.setPixmap(pixmap)
        if self._debug_layer_visible.get("final_overlay", True):
            self._mask_overlay_item.show()
        self._debug_raw_mask_item.setVisible(self._debug_layer_visible.get("raw_mask", False))
        self._debug_cleaned_mask_item.setVisible(self._debug_layer_visible.get("cleaned_mask", False))

    def _set_debug_grayscale_layer(self, item, mask, h, w, tint):
        """Render a single-channel mask as a translucent tinted debug layer."""
        import numpy as np
        from PyQt6.QtGui import QImage, QPixmap
        overlay = np.zeros((h, w, 4), dtype=np.uint8)
        overlay[..., 0] = tint[0]
        overlay[..., 1] = tint[1]
        overlay[..., 2] = tint[2]
        overlay[..., 3] = mask  # use raw mask intensity as alpha -- shows exact pipeline values
        item._debug_data = overlay  # keep a reference to prevent GC
        qimg = QImage(overlay.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        item.setPixmap(QPixmap.fromImage(qimg))

    def set_debug_layer_visible(self, layer: str, visible: bool):
        """Sprint 32B Developer Debug Overlay: toggle one pipeline stage's
        visualization independently of the others."""
        self._debug_layer_visible[layer] = visible
        if layer == "raw_mask":
            self._debug_raw_mask_item.setVisible(visible)
        elif layer == "cleaned_mask":
            self._debug_cleaned_mask_item.setVisible(visible)
        elif layer == "final_overlay":
            self._mask_overlay_item.setVisible(visible and not self._mask_overlay_item.pixmap().isNull())
        elif layer == "points":
            self._debug_points_item.setVisible(visible)
            if visible:
                self._render_debug_points()

    def set_debug_prompt_points(self, points):
        """points: list of (x, y, label) in original-frame coordinates --
        the exact coordinates actually sent to MobileSAM, for the 'Prompt
        Points' Developer Debug Overlay layer."""
        self._last_prompt_points = points
        if self._debug_layer_visible.get("points", False):
            self._render_debug_points()

    def _render_debug_points(self):
        if self._last_frame_size is None:
            return
        w, h = int(self._last_frame_size.width()), int(self._last_frame_size.height())
        from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor as _QColor
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(0)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for px, py, label in self._last_prompt_points:
            color = _QColor(40, 210, 80) if label == 1 else _QColor(255, 50, 50)
            painter.setBrush(color)
            painter.setPen(QPen(_QColor(255, 255, 255), 2))
            painter.drawEllipse(QPointF(px, py), 6, 6)
        painter.end()
        self._debug_points_item.setPixmap(QPixmap.fromImage(img))
        self._debug_points_item.show()

    def clear_interactive_mask(self):
        self._mask_overlay_item.setPixmap(QPixmap())
        self._debug_raw_mask_item.setPixmap(QPixmap())
        self._debug_cleaned_mask_item.setPixmap(QPixmap())
        self._debug_points_item.setPixmap(QPixmap())

    def set_drawing_mode(self, enabled: bool):
        self._drawing_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    def set_mask_mode(self, label: int):
        self._mask_mode = label
            
    def set_interactive_points(self, points: list):
        if not hasattr(self, '_interactive_items'):
            self._interactive_items = []
        
        # Clear previous markers
        for item in self._interactive_items:
            self._scene.removeItem(item)
        self._interactive_items.clear()
        
        for pt in points:
            if pt.get('type') == 'stroke':
                # Sprint 30: Strokes are purely AI prompts, do not render them permanently.
                # They will vanish and be replaced by the AI mask overlay.
                continue
            elif pt.get('type') == 'rectangle':
                rect_data = pt['data']
                label = pt.get('label', 1)
                
                # rect_data is in original-frame (logical) coordinates; this
                # item is parented to _original_item, so it needs to be in
                # THAT item's local pixmap-pixel space, which is smaller than
                # logical space by preview_scale when preview_scale < 1.0.
                # (Bug fix: this used to divide, which grew the rect instead
                # of shrinking it -- invisible at the default 1.0 preview
                # scale, wrong at Half/Quarter Resolution.)
                scale_factor = 1.0 / self._original_item.scale() if self._original_item.scale() > 0 else 1.0
                scene_x1 = rect_data[0] * scale_factor
                scene_y1 = rect_data[1] * scale_factor
                scene_x2 = rect_data[2] * scale_factor
                scene_y2 = rect_data[3] * scale_factor
                
                rect_item = QGraphicsRectItem(QRectF(QPointF(scene_x1, scene_y1), QPointF(scene_x2, scene_y2)))
                color = QColor(40, 210, 80) if label == 1 else QColor(255, 50, 50)
                pen = QPen(color, 2)
                pen.setCosmetic(True)
                rect_item.setPen(pen)
                rect_item.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 50)))
                
                rect_item.setZValue(10.0)
                rect_item.setParentItem(self._original_item)
                self._interactive_items.append(rect_item)

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
        if getattr(self, '_drawing_box', False) and event.button() == Qt.MouseButton.RightButton:
            self._drawing_box = False
            self._scene.removeItem(self._temp_box_item)
            self._temp_box_item = None
            event.accept()
            return
            
        if getattr(self, '_drawing_stroke', False) and event.button() != self._stroke_button:
            self._drawing_stroke = False
            self._scene.removeItem(self._temp_stroke_item)
            self._temp_stroke_item = None
            event.accept()
            return

        if getattr(self, '_drawing_mode', False) and getattr(self, '_prompt_mode', 'stroke') == 'stroke' and event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            # mapToScene() already returns coordinates in the scene's
            # logical (original-frame) coordinate system -- the scene rect
            # is explicitly set to logical_size in load_frame(), and
            # _original_item's own .scale() exists precisely so its
            # on-screen footprint matches that regardless of preview_scale.
            # No further scaling belongs here (bug fix: this used to
            # multiply by preview_scale, silently shrinking every prompt
            # coordinate toward the origin whenever preview quality was
            # anything but "Full Resolution" -- invisible at the default
            # 1.0 scale, badly wrong at Half/Quarter Resolution).
            scene_pos = self.mapToScene(event.position().toPoint())
            px = scene_pos.x()
            py = scene_pos.y()

            self._drawing_stroke = True
            self._stroke_points = [[px, py]]
            self._stroke_button = event.button()
            
            # Start drawing temporary stroke
            mask_mode = getattr(self, '_mask_mode', 1)
            label = mask_mode if event.button() == Qt.MouseButton.LeftButton else (1 if mask_mode == 0 else 0)
            self._stroke_label = label
            color = QColor(40, 210, 80) if label == 1 else QColor(255, 50, 50)
            
            self._temp_path = QPainterPath()
            self._temp_path.moveTo(scene_pos.x(), scene_pos.y())
            self._temp_stroke_item = QGraphicsPathItem(self._temp_path)
            
            pen = QPen(color, 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCosmetic(True)
            self._temp_stroke_item.setPen(pen)
            self._temp_stroke_item.setZValue(15)
            self._scene.addItem(self._temp_stroke_item)
            
            event.accept()
            return
            
        if getattr(self, '_drawing_mode', False) and getattr(self, '_prompt_mode', 'stroke') == 'box' and event.button() == Qt.MouseButton.LeftButton:
            # See the stroke branch above for why no scale_factor is applied.
            scene_pos = self.mapToScene(event.position().toPoint())

            self._drawing_box = True
            self._box_start_scene = scene_pos
            self._box_start_logical = [scene_pos.x(), scene_pos.y()]
            
            self._temp_box_item = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
            pen = QPen(QColor(40, 210, 80), 2)
            pen.setCosmetic(True)
            self._temp_box_item.setPen(pen)
            self._temp_box_item.setBrush(QBrush(QColor(40, 210, 80, 50)))
            self._temp_box_item.setZValue(15)
            self._scene.addItem(self._temp_box_item)
            
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
                hit_rect = QRectF(x - self.HANDLE_HIT_TOLERANCE, 0, self.HANDLE_HIT_TOLERANCE * 2, self.viewport().height())
                if hit_rect.contains(event.position()):
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                    self._comparison_dragging = True
                    event.accept()
                    return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if getattr(self, '_drawing_stroke', False):
            # See mousePressEvent's stroke branch for why no scale_factor.
            scene_pos = self.mapToScene(event.position().toPoint())
            px = scene_pos.x()
            py = scene_pos.y()

            self._stroke_points.append([px, py])
            self._temp_path.lineTo(scene_pos.x(), scene_pos.y())
            self._temp_stroke_item.setPath(self._temp_path)

            # Live preview: report the in-progress stroke so the controller
            # can debounce a background regenerate while the user is still
            # dragging. Cheap to emit on every move -- the controller-side
            # debounce timer, not this call site, controls inference rate.
            self.target_object_live_updated.emit({
                'type': 'stroke',
                'data': list(self._stroke_points),
                'label': getattr(self, '_stroke_label', 1),
            })

            event.accept()
            return
            
        if getattr(self, '_drawing_box', False):
            scene_pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._box_start_scene, scene_pos).normalized()
            self._temp_box_item.setRect(rect)
            event.accept()
            return
            
        if self._comparison_dragging and self._last_frame_size is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            fraction = scene_pos.x() / self._last_frame_size.width()
            self._set_comparison_fraction(fraction)
            event.accept()
            return

        if getattr(self, '_panning', False) and getattr(self, '_pan_start', None) is not None:
            delta = event.position() - self._pan_start
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            self._pan_start = event.position()
            event.accept()
            return

        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event) -> None:
        if getattr(self, '_drawing_stroke', False):
            self._drawing_stroke = False
            self._scene.removeItem(self._temp_stroke_item)
            self._temp_stroke_item = None
            
            mask_mode = getattr(self, '_mask_mode', 1)
            label = mask_mode if self._stroke_button == Qt.MouseButton.LeftButton else (1 if mask_mode == 0 else 0)
            
            if len(self._stroke_points) > 0:
                self.target_object_selected.emit({
                    'type': 'stroke',
                    'data': self._stroke_points,
                    'label': label
                })
            
            event.accept()
            return
            
        if getattr(self, '_drawing_box', False):
            self._drawing_box = False
            self._scene.removeItem(self._temp_box_item)
            self._temp_box_item = None
            
            # See mousePressEvent's stroke branch for why no scale_factor.
            scene_pos = self.mapToScene(event.position().toPoint())
            end_logical = [scene_pos.x(), scene_pos.y()]
            
            x1 = min(self._box_start_logical[0], end_logical[0])
            y1 = min(self._box_start_logical[1], end_logical[1])
            x2 = max(self._box_start_logical[0], end_logical[0])
            y2 = max(self._box_start_logical[1], end_logical[1])
            
            # Box mode always acts as Keep (label 1)
            self.target_object_selected.emit({
                'type': 'rectangle',
                'data': [x1, y1, x2, y2],
                'label': 1
            })
            
            event.accept()
            return
            
        if event.button() == Qt.MouseButton.MiddleButton and getattr(self, '_panning', False):
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and getattr(self, '_comparison_dragging', False):
            self._comparison_dragging = False
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