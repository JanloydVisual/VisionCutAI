"""
AI Status Panel
---------------
Small widget showing AI model status.
Displays Model name, Device (GPU/CPU), and Processing state.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt


class AIStatusPanel(QWidget):
    """
    Displays AI processing status.
    Shows: Model | Device | Status
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(12)

        # Model label
        self.model_label = QLabel("Model: U²-Net")
        self.model_label.setStyleSheet("color: #888; font-size: 11px;")

        # Device label
        self.device_label = QLabel("Device: Checking...")
        self.device_label.setStyleSheet("color: #888; font-size: 11px;")

        # Status indicator
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: #2d7d46; font-size: 11px; font-weight: bold;")

        layout.addWidget(self.model_label)
        layout.addWidget(self.device_label)
        layout.addWidget(self.status_label)

    def set_device(self, device: str, available: bool = True):
        """Update device display."""
        color = "#2d7d46" if available else "#cc3333"
        self.device_label.setText(f"Device: {device}")
        self.device_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_status(self, status: str, processing: bool = False):
        """Update status display."""
        if processing:
            color = "#cc9900"  # Amber for processing
            self.status_label.setText(f"Status: {status}")
        elif status.lower() in ["ready", "complete", "removed"]:
            color = "#2d7d46"  # Green
            self.status_label.setText(f"Status: {status}")
        elif status.lower() in ["error", "failed", "unavailable"]:
            color = "#cc3333"  # Red
            self.status_label.setText(f"Status: {status}")
        else:
            color = "#888"
            self.status_label.setText(f"Status: {status}")

        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")