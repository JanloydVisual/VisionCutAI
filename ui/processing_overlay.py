"""
Processing Overlay
------------------
Modal overlay dialog shown during AI processing.
Displays Processing..., Model, Device, and Progress.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen


class ProcessingOverlay(QDialog):
    """Non-blocking overlay showing AI processing status."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(False)

        self._build_ui()
        self._progress_timer = QTimer()
        self._progress_timer.timeout.connect(self._update_spinner)
        self._spinner_angle = 0

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)

        # Container with dark background
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border: 2px solid #2d7d46;
                border-radius: 12px;
            }
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(16)
        container_layout.setContentsMargins(20, 20, 20, 20)

        # Loading spinner area
        self.spinner_label = QLabel()
        self.spinner_label.setFixedSize(60, 60)
        self.spinner_label.setStyleSheet("border: none; background: transparent;")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Status text
        self.status_label = QLabel("Processing...")
        self.status_label.setStyleSheet("color: #ddd; font-size: 18px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        container_layout.addWidget(self.spinner_label)
        container_layout.addWidget(self.status_label)

        # Model info
        self.model_label = QLabel("Model: U²-Net")
        self.model_label.setStyleSheet("color: #888; font-size: 12px;")
        container_layout.addWidget(self.model_label)

        # Device info
        self.device_label = QLabel("Device: Checking...")
        self.device_label.setStyleSheet("color: #888; font-size: 12px;")
        container_layout.addWidget(self.device_label)

        # Progress bar (hidden initially, shown when progress available)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                background-color: #2b2b2b;
                color: #ddd;
            }
            QProgressBar::chunk {
                background-color: #2d7d46;
                border-radius: 4px;
            }
        """)
        self.progress_bar.hide()
        container_layout.addWidget(self.progress_bar)

        # Progress text
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.progress_label)

        layout.addWidget(self.container)

    def set_model(self, model_name: str):
        """Update the model display."""
        self.model_label.setText(f"Model: {model_name}")

    def set_device(self, device_name: str):
        """Update the device display."""
        self.device_label.setText(f"Device: {device_name}")

    def set_status(self, status: str):
        """Update the status text."""
        self.status_label.setText(status)

    def set_progress(self, current: int, total: int):
        """Update the progress bar."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_label.setText(f"Frame {current} of {total}")
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
            self.progress_bar.setValue(0)
            self.progress_label.setText("")

    def showEvent(self, event):
        """Start spinner animation when shown."""
        self._spinner_angle = 0
        self._progress_timer.start(50)  # Update every 50ms
        super().showEvent(event)

    def hideEvent(self, event):
        """Stop spinner animation when hidden."""
        self._progress_timer.stop()
        super().hideEvent(event)

    def _update_spinner(self):
        """Update spinner animation."""
        self._spinner_angle = (self._spinner_angle + 15) % 360
        self.spinner_label.update()

    def paintEvent(self, event):
        """Paint the loading spinner."""
        painter = QPainter(self.spinner_label)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw spinning arc
        pen = QPen(QColor(45, 125, 70), 4)
        painter.setPen(pen)

        rect = self.spinner_label.rect().adjusted(5, 5, -5, -5)
        span = 60
        painter.drawArc(rect, self._spinner_angle * 16, span * 16)

        painter.end()

    def resizeEvent(self, event):
        """Center overlay on parent."""
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                parent_rect.center() - self.rect().center() - self.parent().mapToGlobal(self.parent().rect().topLeft()).toPointF().toPoint()
            )
        super().resizeEvent(event)