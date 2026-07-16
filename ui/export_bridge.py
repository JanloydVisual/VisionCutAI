"""
ExportBridge
------------
Bridges the plain core.signals.Signal (ExportManager) to Qt signals.
This allows the UI to receive export progress without the core
knowing anything about Qt.
"""

from PyQt6.QtCore import QObject, pyqtSignal


class ExportBridge(QObject):
    """Adapts ExportManager signals to Qt signals for UI updates."""

    export_started = pyqtSignal(str)    # output_dir
    export_progress = pyqtSignal(int, int)  # frame_index, total_frames
    export_finished = pyqtSignal(str) # output_dir
    export_error = pyqtSignal(str)    # error_message
    export_cancelled = pyqtSignal(str, int)  # output_dir, frames_exported

    def __init__(self, export_manager, parent=None):
        super().__init__(parent)
        export_manager.export_started.connect(self._on_started)
        export_manager.export_progress.connect(self._on_progress)
        export_manager.export_finished.connect(self._on_finished)
        export_manager.export_error.connect(self._on_error)
        export_manager.export_cancelled.connect(self._on_cancelled)
        export_manager.export_image_completed.connect(self._on_image_completed)

    def _on_started(self, output_dir: str):
        self.export_started.emit(output_dir)

    def _on_progress(self, frame_index: int, total_frames: int):
        self.export_progress.emit(frame_index, total_frames)

    def _on_finished(self, output_dir: str):
        self.export_finished.emit(output_dir)

    def _on_error(self, error: str):
        self.export_error.emit(error)

    def _on_cancelled(self, output_dir: str, frames_exported: int):
        self.export_cancelled.emit(output_dir, frames_exported)

    def _on_image_completed(self, output_path: str):
        self.export_finished.emit(output_path)
