import os
import threading
import time
from pathlib import Path
import subprocess

import cv2
import numpy as np

from core.signals import Signal


class VideoExporter:
    """
    Exports video frames as WebM or MOV via FFmpeg.
    Runs in a background thread to keep UI responsive.
    """

    def __init__(self, output_dir: str, output_name: str, output_format: str, processor=None, timeline=None, tracking_engine=None):
        self.output_dir = Path(output_dir)
        self.output_name = output_name
        self.output_format = output_format
        self.processor = processor
        self.timeline = timeline
        # Sprint: Audit 1.0 fix -- see png_sequence_exporter.py for why this
        # matters: without it, export used a single frozen sam_prompt
        # snapshot instead of the per-frame tracked prompt.
        self.tracking_engine = tracking_engine
        self._stop_event = threading.Event()
        self._keep_frames_on_cancel = True
        self._thread = None

        # Signals for UI feedback
        self.progress_updated = Signal()
        self.export_completed = Signal()
        self.export_failed = Signal()
        self.export_cancelled = Signal()

        # Timing tracking
        self._start_time = None
        self._current_frame = 0
        self._total_frames = 0
        self._video_path = None

    def _read_frame(self, cap, frame_index: int) -> np.ndarray | None:
        if cap is None:
            return None
            
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = cap.read()
        return frame if success else None

    def _process_frame(self, frame: np.ndarray, custom_prompt=None) -> np.ndarray:
        if self.processor is None:
            h, w = frame.shape[:2]
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
            rgb = frame[:, :, ::-1]
            return np.concatenate([rgb, alpha], axis=2)
        return self.processor.process(frame, custom_prompt=custom_prompt)

    def _tracked_prompt_for(self, source_frame: int):
        """See png_sequence_exporter.py's _tracked_prompt_for -- same fix,
        same reasoning."""
        if self.tracking_engine is None:
            return None
        return self.tracking_engine.get_tracked_prompt(source_frame)

    def export(self, video_path: str, start_frame: int = 0, end_frame: int | None = None):
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
        caps = {}  # Cache cv2.VideoCapture objects by source_path
        proc = None
        output_path = None
        frames_exported = 0
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Determine total frames and video properties
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
                # For timeline, we always export 0 to total_frames - 1 unless subset is requested
                start_frame = max(0, start_frame)
                if end_frame is None:
                    end_frame = max(0, total_frames - 1)
                end_frame = min(end_frame, max(0, total_frames - 1))

            # Grab properties from the primary video path as a baseline
            baseline_cap = caps.get(video_path)
            if not baseline_cap:
                baseline_cap = cv2.VideoCapture(video_path)
                if not baseline_cap.isOpened():
                    raise FileNotFoundError(f"Cannot open baseline video: {video_path}")
                caps[video_path] = baseline_cap

            fps = baseline_cap.get(cv2.CAP_PROP_FPS)
            width = int(baseline_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(baseline_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if self.output_format == "Transparent WebM":
                output_path = self.output_dir / f"{self.output_name}.webm"
                cmd = [
                    'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{width}x{height}', '-pix_fmt', 'bgra', '-r', str(fps),
                    '-i', '-', '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p',
                    str(output_path)
                ]
            else: # MOV Alpha
                output_path = self.output_dir / f"{self.output_name}.mov"
                cmd = [
                    'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{width}x{height}', '-pix_fmt', 'bgra', '-r', str(fps),
                    '-i', '-', '-c:v', 'prores_ks', '-profile:v', '4444', 
                    '-pix_fmt', 'yuva444p10le', str(output_path)
                ]
                
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL,
                startupinfo=startupinfo
            )

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
                    proc.stdin.write(bgra.tobytes())
                    frames_exported += 1
                else:
                    processed = self._process_frame(frame, custom_prompt=self._tracked_prompt_for(source_frame))
                    if processed is not None:
                        if processed.shape[2] == 4:
                            bgra = cv2.cvtColor(processed, cv2.COLOR_RGBA2BGRA)
                        else:
                            bgra = processed
                        proc.stdin.write(bgra.tobytes())
                        frames_exported += 1

                self.progress_updated.emit(frame_idx + 1, total_frames)

            if proc is not None:
                if proc.stdin is not None:
                    proc.stdin.close()
                proc.wait(timeout=300)

            if self._stop_event.is_set():
                if not self._keep_frames_on_cancel:
                    try:
                        if output_path is not None:
                            output_path.unlink()
                    except Exception:
                        pass
                self.export_cancelled.emit(str(self.output_dir), frames_exported)
            else:
                self.export_completed.emit(str(self.output_dir))

        except Exception as e:
            self.export_failed.emit(str(e))
        finally:
            for cap in caps.values():
                cap.release()
            if proc is not None and proc.poll() is None:
                proc.kill()

    def stop(self, keep_frames: bool = True):
        self._keep_frames_on_cancel = keep_frames
        self._stop_event.set()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_elapsed_time(self) -> float:
        if self._start_time is None:
            return 0
        return time.time() - self._start_time

    def get_eta(self) -> float:
        if self._start_time is None or self._total_frames == 0 or self._current_frame == 0:
            return 0
        elapsed = self.get_elapsed_time()
        rate = self._current_frame / elapsed
        if rate == 0:
            return 0
        remaining = self._total_frames - self._current_frame
        return remaining / rate
