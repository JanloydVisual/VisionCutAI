"""
Exporter Manager
---------------
High-level export coordinator that integrates with the app controller.
Provides a simple interface for the UI to trigger exports.
"""

from core.export import PngSequenceExporter
from core.frame_processor import PassthroughProcessor
from core.signals import Signal


class ExportManager:
    """
    Coordinates export operations.
    Keeps export logic separate from UI and core systems.
    """

    def __init__(self, project, background_removal_processor=None):
        self.project = project
        self.background_removal_processor = background_removal_processor

        # Current active exporter
        self._exporter = None
        self._last_output_path = None

        # Signals for UI integration
        self.export_started = Signal()      # Emits (output_dir)
        self.export_progress = Signal()      # Emits (frame_index, total_frames)
        self.export_finished = Signal()      # Emits (output_dir)
        self.export_error = Signal()         # Emits (error_message)
        self.export_cancelled = Signal()     # Emits (output_dir, frames_exported)
        self.export_image_completed = Signal() # Emits (output_path) - for single image export

        # Export info for UI
        self._output_dir = ""
        self._frames_exported = 0

    def _on_image_completed(self, output_path: str):
        self.export_finished.emit(output_path)

    def start_export(self, video_path: str, output_dir: str, 
                     output_name: str = "export", output_format: str = "PNG Sequence (Video)",
                     start_frame: int = 0, end_frame: int = None):
        """
        Start export - unified entry point.
        
        Args:
            video_path: Path to source video or image
            output_dir: Directory for output frames
            output_name: Base name for output file
            output_format: Selected format from UI
            start_frame: First frame to export (default 0)
            end_frame: Last frame to export (default: all frames)
        """
        if self.is_exporting():
            self.export_error.emit("Export already in progress")
            return

        if output_format == "PNG Sequence (Video)":
            self.export_png_sequence(video_path, output_dir, start_frame, end_frame)
        elif output_format in ["Transparent WebM", "MOV Alpha"]:
            self.export_video(video_path, output_dir, output_name, output_format, start_frame, end_frame)

    def export_image(self, image_path: str, output_dir: str, output_name: str = "export"):
        """
        Export a single image as PNG.
        
        Args:
            image_path: Path to source image
            output_dir: Directory for output
            output_name: Base name for output file (without extension)
        """
        from core.export.png_sequence_exporter import PngSequenceExporter
        
        # Determine processor: use background removal if available
        processor = PassthroughProcessor()
        if self.background_removal_processor is not None:
            try:
                processor = self.background_removal_processor
            except Exception:
                pass  # Fall back to passthrough on error

        self._exporter = PngSequenceExporter(output_dir, processor=processor)

        # Wire up signals
        self._exporter.progress_updated.connect(self._on_progress)
        self._exporter.export_completed.connect(self._on_completed)
        self._exporter.export_failed.connect(self._on_failed)
        self._exporter.export_cancelled.connect(self._on_cancelled)
        self._exporter.export_image_completed.connect(self._on_image_completed)

        self.export_started.emit(output_dir)
        self._exporter.export_image(image_path, output_name)

    def export_png_sequence(self, video_path: str, output_dir: str, 
                            start_frame: int = 0, end_frame: int = None):
        """
        Export video frames as transparent PNG sequence.
        
        Args:
            video_path: Path to source video
            output_dir: Directory for output frames
            start_frame: First frame to export (default 0)
            end_frame: Last frame to export (default: all frames)
        """
        # Determine processor: use background removal if available
        processor = PassthroughProcessor()
        if self.background_removal_processor is not None:
            try:
                processor = self.background_removal_processor
            except Exception:
                pass  # Fall back to passthrough on error

        self._exporter = PngSequenceExporter(output_dir, processor=processor, timeline=self.project.timeline)

        # Wire up signals
        self._exporter.progress_updated.connect(self._on_progress)
        self._exporter.export_completed.connect(self._on_completed)
        self._exporter.export_failed.connect(self._on_failed)
        self._exporter.export_cancelled.connect(self._on_cancelled)

        self.export_started.emit(output_dir)
        self._exporter.export(video_path, start_frame, end_frame)

    def export_video(self, video_path: str, output_dir: str, output_name: str,
                     output_format: str, start_frame: int = 0, end_frame: int = None):
        """
        Export video frames as WebM or MOV via FFmpeg.
        """
        from core.export.video_exporter import VideoExporter
        
        processor = PassthroughProcessor()
        if self.background_removal_processor is not None:
            try:
                processor = self.background_removal_processor
            except Exception:
                pass

        self._exporter = VideoExporter(output_dir, output_name, output_format, processor=processor, timeline=self.project.timeline)

        self._exporter.progress_updated.connect(self._on_progress)
        self._exporter.export_completed.connect(self._on_completed)
        self._exporter.export_failed.connect(self._on_failed)
        self._exporter.export_cancelled.connect(self._on_cancelled)

        self.export_started.emit(output_dir)
        self._exporter.export(video_path, start_frame, end_frame)

    def _on_progress(self, frame_index: int, total_frames: int):
        self.export_progress.emit(frame_index, total_frames)

    def _on_completed(self, output_dir: str):
        self.export_finished.emit(output_dir)

    def _on_failed(self, error: str):
        self.export_error.emit(error)

    def _on_cancelled(self, output_dir: str, frames_exported: int):
        """Handle export cancellation."""
        self._frames_exported = frames_exported
        self.export_cancelled.emit(output_dir, frames_exported)

    def cancel_export(self, keep_frames: bool = True):
        """
        Cancel the current export.
        
        Args:
            keep_frames: If True, keep exported frames. If False, delete them.
        """
        if self._exporter is not None and self._exporter.is_running():
            self._exporter.stop(keep_frames=keep_frames)

    def is_exporting(self) -> bool:
        """Check if an export is in progress."""
        return self._exporter is not None and self._exporter.is_running()

    def get_elapsed_time(self) -> float:
        """Return elapsed time in seconds."""
        if self._exporter is not None:
            return self._exporter.get_elapsed_time()
        return 0

    def get_eta(self) -> float:
        """Return estimated time remaining in seconds."""
        if self._exporter is not None:
            return self._exporter.get_eta()
        return 0

    def get_frames_exported(self) -> int:
        """Return number of frames exported before cancellation."""
        return self._frames_exported