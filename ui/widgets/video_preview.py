"""
VideoPreview
------------
Owns the ViewerWidget (zoom/pan/comparison) and OverlayCanvas,
stacked together, plus the ViewerControls bar beneath and PreviewToggle.

Public API is unchanged from prior milestones; set_processed_frame
is a new additive method forwarding to the already-existing
ViewerWidget.set_processed_frame().
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedLayout, QSizePolicy, QHBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import pyqtSignal

from ui.widgets.overlay_canvas import OverlayCanvas
from ui.widgets.viewer_widget import ViewerWidget
from ui.widgets.viewer_controls import ViewerControls
from ui.widgets.preview_toggle import PreviewToggle


class VideoPreview(QWidget):
    target_object_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        stack_container = QWidget()
        self._stack_layout = QStackedLayout(stack_container)
        self._stack_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.viewer = ViewerWidget()
        self.viewer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.overlay = OverlayCanvas(stack_container)

        self._stack_layout.addWidget(self.viewer)
        self._stack_layout.addWidget(self.overlay)

        root.addWidget(stack_container, stretch=1)

        # Top bar with preview toggle
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(8, 4, 8, 4)
        self.preview_toggle = PreviewToggle()
        top_bar.addWidget(self.preview_toggle)
        top_bar.addStretch()
        root.addLayout(top_bar)

        self.controls = ViewerControls()
        root.addWidget(self.controls)

        self.controls.fit_clicked.connect(self.viewer.fit_to_window)
        self.controls.zoom_100_clicked.connect(self.viewer.zoom_100)
        self.controls.zoom_200_clicked.connect(self.viewer.zoom_200)
        self.controls.reset_clicked.connect(self.viewer.reset_view)
        self.viewer.zoom_changed.connect(self.controls.set_zoom_label)
        self.viewer.target_object_selected.connect(self.target_object_selected.emit)
        # Connect preview toggle
        self.preview_toggle.mode_changed.connect(self._on_preview_mode_changed)

    def load_frame(self, pixmap: QPixmap, scale_factor: float = 1.0) -> None:
        self.viewer.load_frame(pixmap, scale_factor)

    def set_processed_frame(self, pixmap: QPixmap, scale_factor: float = 1.0) -> None:
        self.viewer.set_processed_frame(pixmap, scale_factor)

    def show_processed_preview(self) -> None:
        self.viewer.show_processed_preview()
        self.preview_toggle.set_mode("ai")

    def show_original_preview(self) -> None:
        self.viewer.show_original_preview()
        self.preview_toggle.set_mode("original")
        
    def show_split_preview(self) -> None:
        self.viewer.show_split_preview()
        self.preview_toggle.set_mode("split")

    def set_drawing_mode(self, enabled: bool) -> None:
        self.viewer.set_drawing_mode(enabled)

    def fit_to_window(self) -> None:
        self.viewer.fit_to_window()

    def clear(self) -> None:
        self.viewer.clear()

    def get_overlay(self) -> OverlayCanvas:
        return self.overlay

    def _on_preview_mode_changed(self, mode: str):
        """Handle preview toggle changes."""
        self.viewer.set_preview_mode(mode)