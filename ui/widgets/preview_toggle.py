"""
Preview Toggle
--------------
Toggle button for switching between Original and AI Result views.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt


class PreviewToggle(QWidget):
    """
    Toggle widget for switching between Original and AI Result previews.
    """

    mode_changed = pyqtSignal(str)  # 'original', 'split', 'ai'

    def __init__(self, parent=None):
        super().__init__(parent)

        self._mode = "original"

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.original_button = QPushButton("Original")
        self.original_button.setCheckable(True)
        self.original_button.setChecked(True)
        self.original_button.setFixedWidth(100)
        self.original_button.clicked.connect(lambda: self.set_mode("original"))
        layout.addWidget(self.original_button)

        self.split_button = QPushButton("Split View")
        self.split_button.setCheckable(True)
        self.split_button.setChecked(False)
        self.split_button.setFixedWidth(100)
        self.split_button.clicked.connect(lambda: self.set_mode("split"))
        layout.addWidget(self.split_button)

        self.result_button = QPushButton("AI Result")
        self.result_button.setCheckable(True)
        self.result_button.setChecked(False)
        self.result_button.setFixedWidth(100)
        self.result_button.clicked.connect(lambda: self.set_mode("ai"))
        layout.addWidget(self.result_button)

        self._update_styles()

    def _update_styles(self):
        """Update button styles based on selection state."""
        for btn in [self.original_button, self.split_button, self.result_button]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    border: 1px solid #444;
                    background-color: #2b2b2b;
                    color: #888;
                    font-size: 12px;
                }
                QPushButton:checked {
                    background-color: #2d7d46;
                    color: white;
                    font-weight: bold;
                }
            """)

    def set_mode(self, mode: str):
        """Set the preview mode ('original', 'split', 'ai')."""
        if self._mode == mode:
            return

        self._mode = mode
        self.original_button.setChecked(mode == "original")
        self.split_button.setChecked(mode == "split")
        self.result_button.setChecked(mode == "ai")
        self.mode_changed.emit(mode)

    def current_mode(self) -> str:
        """Return the current preview mode."""
        return self._mode