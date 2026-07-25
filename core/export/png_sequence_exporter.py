"""
PNG Sequence Exporter
--------------------
Exports video frames as transparent PNG sequence.
Designed for DaVinci Resolve Free compatibility.

Architecture:
    Video File → Frame Reader → Processor (optional) → RGBA Frames → PNG Writer
"""

import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from core.signals import Signal
from core.media_loader import is_image


class PngSequenceExporter:
    """
    Exports video frames as transparent PNG sequence.
    Runs in a background thread to keep UI responsive.
    """

    def __init__(self, output_dir: str, processor=None, timeline=None, tracking_engine=None):
        self.output_dir = Path(output_dir)
        self.processor = processor  # Optional FrameProcessor (e.g., BackgroundRemovalProcessor)
        self.timeline = timeline
        # Sprint: Audit 1.0 fix -- without this, export always used a single
        # frozen sam_prompt snapshot instead of the per-frame tracked prompt
        # that live preview and the render cache both correctly use, so
        # exported output could look nothing like preview for any clip where
        # the subject moves.
        self.tracking_engine = tracking_engine
        self._stop_event = threading.Event()
        self._keep_frames_on_cancel = True
        self._thread = None
        self._progress_callback = None

        # Signals for UI feedback (no Qt dependency)
        self.progress_updated = Signal()  # Emits (frame_index, total_frames)
        self.export_completed = Signal()  # Emits (output_dir) for video export
        self.export_failed = Signal()     # Emits (error_message)
        self.export_cancelled = Signal()  # Emits (output_dir, frames_exported)
        self.export_image_completed = Signal()  # Emits (output_path) for image export

        # Timing tracking
        self._start_time = None
        self._current_frame = 0
        self._total_frames = 0
        self._video_path = None
        self._is_image_export = False
        self._image_output_name = "export"

    def _read_frame(self, cap, frame_index: int) -> np.ndarray | None:
        """Read a single frame from the video at the given index."""
        if cap is None:
            # Image mode - read the whole image
            frame = cv2.imread(self.video_path, cv2.IMREAD_UNCHANGED)
            if frame is not None:
                return frame
            return None
            
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = cap.read()
        return frame if success else None

    def _process_frame(self, frame: np.ndarray, custom_prompt=None) -> np.ndarray:
        """Apply background removal if processor is set, otherwise passthrough."""
        if self.processor is None:
            # Add alpha channel if no processor (RGBA passthrough)
            h, w = frame.shape[:2]
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
            rgb = frame[:, :, ::-1]  # BGR to RGB
            return np.concatenate([rgb, alpha], axis=2)
        return self.processor.process(frame, custom_prompt=custom_prompt)

    def _tracked_prompt_for(self, source_frame: int):
        """Look up the per-frame tracked SAM prompt for source_frame, the
        same way live playback (AppController._process_frame) and the
        render cache (AIRenderWorker) both do -- so export doesn't fall back
        to a single frozen prompt snapshot for the whole clip."""
        if self.tracking_engine is None:
            return None
        return self.tracking_engine.get_tracked_prompt(source_frame)

    def _save_png(self, frame: np.ndarray, frame_index: int) -> bool:
        """Save RGBA frame as PNG."""
        # Convert to BGRA for OpenCV
        bgra = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGRA) if frame.shape[2] == 4 else frame
        output_path = self.output_dir / f"frame_{frame_index:06d}.png"
        return cv2.imwrite(str(output_path), bgra)

    def export_image(self, image_path: str, output_name: str = "export"):
        """
        Export a single image as PNG with custom output name.
        
        Args:
            image_path: Path to source image
            output_name: Base name for output file (without extension)
        """
        if self._thread is not None and self._thread.is_alive():
            self.export_failed.emit("Export already in progress")
            return

        self.video_path = image_path
        self._is_image_export = True
        self._image_output_name = output_name
        self._stop_event.clear()
        self._start_time = time.time()
        self._current_frame = 0
        self._total_frames = 0
        self._thread = threading.Thread(
            target=self._export_image_worker,
            daemon=True
        )
        self._thread.start()

    def _save_image_png(self, frame: np.ndarray, output_name: str) -> bool:
        """Save RGBA frame as PNG with custom output name."""
        # Convert to BGRA for OpenCV
        bgra = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGRA) if frame.shape[2] == 4 else frame
        output_path = self.output_dir / f"{output_name}.png"
        return cv2.imwrite(str(output_path), bgra)

    def _export_image_worker(self):
        """Background worker that reads and saves a single image."""
        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Read the image
            frame = cv2.imread(self.video_path, cv2.IMREAD_UNCHANGED)
            if frame is None:
                self.export_failed.emit(f"Cannot read image: {self.video_path}")
                return

            # Process the frame (apply background removal if available)
            processed = self._process_frame(frame)
            if processed is None:
                self.export_failed.emit("Image processing failed")
                return

            # Save as PNG with custom output name
            if self._save_image_png(processed, self._image_output_name):
                self.progress_updated.emit(1, 1)
                output_path = str(self.output_dir / f"{self._image_output_name}.png")
                self.export_image_completed.emit(output_path)
            else:
                self.export_failed.emit("Failed to save image")

        except Exception as e:
            self.export_failed.emit(str(e))

    def export(self, video_path: str, start_frame: int = 0, end_frame: int | None = None):
        """
        Start export in a background thread.
        
        Args:
            video_path: Path to source video or image
            start_frame: First frame to export (default 0)
            end_frame: Last frame to export (default: all frames)
        """
        if self._thread is not None and self._thread.is_alive():
            self.export_failed.emit("Export already in progress")
            return

        self.video_path = video_path
        self._stop_event.clear()
        self._start_time = time.time()
        self._current_frame = 0
        self._total_frames = 0
        self._thread = threading.Thread(
            target=self._export_worker,
            args=(video_path, start_frame, end_frame),
            daemon=True
        )
        self._thread.start()

    def _export_worker(self, video_path: str, start_frame: int, end_frame: int | None):
        """Background worker that reads, processes, and saves frames."""
        caps = {}  # Cache cv2.VideoCapture objects
        frames_exported = 0
        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Check if this is an image (single frame)
            if is_image(video_path):
                # Image export - single frame
                total_frames = 1
                frame = self._read_frame(None, 0)
                
                if frame is not None:
                    processed = self._process_frame(frame)
                    if processed is not None:
                        self._save_png(processed, 0)
                        frames_exported = 1
                
                self.progress_updated.emit(frames_exported, total_frames)
                self.export_completed.emit(str(self.output_dir))
                return

            # Video/Timeline export - multiple frames
            if self.timeline is not None:
                total_frames = self.timeline.total_timeline_duration()
            else:
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    raise FileNotFoundError(f"Cannot open video: {video_path}")
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                caps[video_path] = cap

            self._total_frames = total_frames
            
            if self.timeline is None:
                if end_frame is None:
                    end_frame = total_frames - 1
                end_frame = min(end_frame, total_frames - 1)
            else:
                start_frame = max(0, start_frame)
                if end_frame is None:
                    end_frame = max(0, total_frames - 1)
                end_frame = min(end_frame, max(0, total_frames - 1))

            # Grab properties from the primary video path as a baseline for blank frames
            baseline_cap = caps.get(video_path)
            if not baseline_cap:
                baseline_cap = cv2.VideoCapture(video_path)
                if not baseline_cap.isOpened():
                    raise FileNotFoundError(f"Cannot open baseline video: {video_path}")
                caps[video_path] = baseline_cap

            width = int(baseline_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(baseline_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self._current_frame = start_frame
            for frame_idx in range(start_frame, end_frame + 1):
                if self._stop_event.is_set():
                    break

                self._current_frame = frame_idx
                
                frame = None
                source_frame = frame_idx
                if self.timeline is not None:
                    clip = self.timeline.clip_at_timeline_frame(frame_idx)
                    if clip is not None:
                        source_frame = clip.start_frame + frame_idx - clip.timeline_start_frame
                        if clip.source_path not in caps:
                            cap = cv2.VideoCapture(clip.source_path)
                            caps[clip.source_path] = cap

                        frame = self._read_frame(caps[clip.source_path], source_frame)
                else:
                    frame = self._read_frame(caps[video_path], frame_idx)

                # Output blank frame if gap or read failed
                if frame is None:
                    bgra = np.zeros((height, width, 4), dtype=np.uint8)
                    output_path = self.output_dir / f"frame_{frame_idx:06d}.png"
                    cv2.imwrite(str(output_path), bgra)
                    frames_exported += 1
                else:
                    processed = self._process_frame(frame, custom_prompt=self._tracked_prompt_for(source_frame))
                    if processed is not None:
                        self._save_png(processed, frame_idx)
                        frames_exported += 1

                self.progress_updated.emit(frame_idx + 1, total_frames)  # +1 for 1-indexed display

            if self._stop_event.is_set():
                if not self._keep_frames_on_cancel:
                    self.cleanup_export(keep_frames=False)
                self.export_cancelled.emit(str(self.output_dir), frames_exported)
            else:
                self.export_completed.emit(str(self.output_dir))

        except Exception as e:
            self.export_failed.emit(str(e))
        finally:
            for cap in caps.values():
                cap.release()

    def stop(self, keep_frames: bool = True):
        """Signal the export thread to stop."""
        self._keep_frames_on_cancel = keep_frames
        self._stop_event.set()

    def is_running(self) -> bool:
        """Check if export is in progress."""
        return self._thread is not None and self._thread.is_alive()

    def get_elapsed_time(self) -> float:
        """Return elapsed time in seconds."""
        if self._start_time is None:
            return 0
        return time.time() - self._start_time

    def get_eta(self) -> float:
        """Return estimated time remaining in seconds."""
        if self._start_time is None or self._total_frames == 0 or self._current_frame == 0:
            return 0
        elapsed = self.get_elapsed_time()
        rate = self._current_frame / elapsed
        if rate == 0:
            return 0
        remaining = self._total_frames - self._current_frame
        return remaining / rate

    def cleanup_export(self, keep_frames: bool = True):
        """
        Clean up incomplete export.
        
        Args:
            keep_frames: If True, leave exported frames. If False, delete all frames in output directory.
        """
        if not keep_frames and self.output_dir.exists():
            for f in self.output_dir.glob("frame_*.png"):
                try:
                    f.unlink()
                except Exception:
                    pass