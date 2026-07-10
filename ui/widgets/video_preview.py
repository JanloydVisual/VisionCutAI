"""
VideoPreview
------------
Owns the ViewerWidget (zoom/pan/comparison) and OverlayCanvas,
stacked together, plus the ViewerControls bar beneath.
Public API is unchanged from prior milestones; set_processed_frame
is a new additive method forwarding to the already-existing
ViewerWidget.set_processed_frame().
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedLayout, QSizePolicy
from PyQt6.QtGui import QPixmap

from ui.widgets.overlay_canvas import OverlayCanvas
from ui.widgets.viewer_widget import ViewerWidget
from ui.widgets.viewer_controls import ViewerControls


class VideoPreview(QWidget):
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

        self.controls = ViewerControls()
        root.addWidget(self.controls)

        self.controls.fit_clicked.connect(self.viewer.fit_to_window)
        self.controls.zoom_100_clicked.connect(self.viewer.zoom_100)
        self.controls.zoom_200_clicked.connect(self.viewer.zoom_200)
        self.controls.reset_clicked.connect(self.viewer.reset_view)
        self.viewer.zoom_changed.connect(self.controls.set_zoom_label)

    def load_frame(self, pixmap: QPixmap) -> None:
        self.viewer.load_frame(pixmap)

    def set_processed_frame(self, pixmap: QPixmap) -> None:
        self.viewer.set_processed_frame(pixmap)

    def clear(self) -> None:
        self.viewer.clear()

    def get_overlay(self) -> OverlayCanvas:
        return self.overlay
