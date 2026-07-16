"""
Export Progress Dialog
----------------------
Dialog showing export progress with cancel button.
Includes elapsed time and estimated time remaining.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import time

from ui.cancel_export_dialog import CancelExportDialog


class ExportProgressDialog(QDialog):
    """Progress dialog for export operations with cancel support."""

    cancelled = pyqtSignal(bool)  # keep_frames parameter

    def __init__(self, parent=None, is_video: bool = True):
        super().__init__(parent)
        self._start_time = time.time()
        self._current_frame = 0
        self._total_frames = 0
        self._export_running = False
        self._is_video = is_video

        self.setWindowTitle("Export Progress")
        self.setModal(True)
        self.resize(350, 180)
        self.setMinimumWidth(300)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Exporting...")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ddd;")
        layout.addWidget(title)

        # Progress bar
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
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #2d7d46;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Progress details
        self.frame_label = QLabel("Frame: 0 / 0")
        self.frame_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.frame_label)

        self.time_label = QLabel("Elapsed: 0s | ETA: --")
        self.time_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.time_label)

        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #cc3333;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff4444;
            }
        """)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Timer for updating time
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)
        self._timer.start(1000)  # Update every second

    def set_progress(self, current_frame: int, total_frames: int):
        """Update progress display."""
        self._current_frame = current_frame
        self._total_frames = total_frames

        percentage = int((current_frame / total_frames) * 100) if total_frames > 0 else 0
        self.progress_bar.setValue(percentage)
        
        if percentage == 100 and self._is_video:
            self.frame_label.setText("Finalizing video file... please wait")
        else:
            self.frame_label.setText(f"Frame: {current_frame} / {total_frames}")

    def _update_time(self):
        """Update elapsed time and ETA."""
        elapsed = int(time.time() - self._start_time)
        elapsed_str = self._format_time(elapsed)
        
        if self._current_frame > 0 and self._total_frames > 0:
            rate = self._current_frame / elapsed if elapsed > 0 else 0
            remaining = self._total_frames - self._current_frame
            eta = int(remaining / rate) if rate > 0 else 0
            eta_str = self._format_time(eta)
        else:
            eta_str = "--"

        self.time_label.setText(f"Elapsed: {elapsed_str} | ETA: {eta_str}")

    def _format_time(self, seconds: int) -> str:
        """Format seconds to human readable time."""
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"

    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        keep_frames = True  # Default
        
        if not self._is_video:
            # For PNG sequence, ask about keeping frames
            dialog = CancelExportDialog(self, is_video=False)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                keep_frames = dialog.get_keep_frames()
            else:
                return  # User chose to continue exporting

        self.cancelled.emit(keep_frames)
        self._export_running = False
        self.reject()

    def closeEvent(self, event):
        """Handle dialog close."""
        self._timer.stop()
        super().closeEvent(event)