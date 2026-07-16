import os
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

class RenderCacheWorker(QThread):
    progress_updated = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(bool, str)         # success, message

    def __init__(self, timeline, cache_dir: Path, preview_scale: float, processor=None, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.cache_dir = cache_dir
        self.preview_scale = preview_scale
        self.processor = processor
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        try:
            
            # Find the max timeline frame
            max_timeline_frame = 0
            for track in self.timeline.tracks:
                for clip in track.clips:
                    if hasattr(clip, 'end_frame') and clip.timeline_end_frame > max_timeline_frame:
                        max_timeline_frame = clip.timeline_end_frame

            if max_timeline_frame == 0:
                self.finished.emit(True, "Empty timeline")
                return

            caps = {}
            total_frames = max_timeline_frame + 1
            
            for tf in range(total_frames):
                if self._cancel_requested:
                    self.finished.emit(False, "Cancelled by user")
                    break
                    
                clip = self.timeline.clip_at_timeline_frame(tf)
                if clip is None or not hasattr(clip, 'start_frame'):
                    # Empty space or audio clip
                    # Let's save a blank frame or just skip caching empty frames
                    self.progress_updated.emit(tf + 1, total_frames)
                    continue

                source_path = clip.source_path
                if source_path not in caps:
                    caps[source_path] = cv2.VideoCapture(source_path)

                cap = caps[source_path]
                source_frame = clip.start_frame + (tf - clip.timeline_start_frame)
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, source_frame)
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # Scale down for fast preview caching
                    if self.preview_scale < 1.0:
                        h, w = frame.shape[:2]
                        new_w, new_h = int(w * self.preview_scale), int(h * self.preview_scale)
                        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

                    if clip.background_removed:
                        if self.processor:
                            rgba = self.processor.process(frame)
                        else:
                            rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
                        save_frame = rgba
                    else:
                        # Convert to RGBA for consistent PNG format
                        rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
                        save_frame = rgba
                        
                    out_path = self.cache_dir / f"frame_{tf:06d}.png"
                    cv2.imwrite(str(out_path), save_frame)
                    
                self.progress_updated.emit(tf + 1, total_frames)
                
            for cap in caps.values():
                cap.release()

            if not self._cancel_requested:
                self.finished.emit(True, "Render Cache Complete")

        except Exception as e:
            self.finished.emit(False, str(e))


class RenderCache(QObject):
    def __init__(self):
        super().__init__()
        self.cache_dir = Path(tempfile.gettempdir()) / "VisionCutAI_Cache"
        self.worker = None
        self.cached_frames = set()
        self._ensure_dir()

    def _ensure_dir(self):
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True)

    def clear(self):
        """Wipe the cache directory."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir, ignore_errors=True)
        self.cached_frames.clear()
        self._ensure_dir()

    def has_frame(self, timeline_frame: int) -> bool:
        """Check if a frame exists in the cache."""
        return timeline_frame in self.cached_frames

    def get_frame(self, timeline_frame: int):
        """Read a frame from the cache. Returns RGBA numpy array or None."""
        if timeline_frame not in self.cached_frames:
            return None
        frame_path = self.cache_dir / f"frame_{timeline_frame:06d}.png"
        if frame_path.exists():
            return cv2.imread(str(frame_path), cv2.IMREAD_UNCHANGED)
        return None

    def start_caching(self, timeline, preview_scale: float, processor=None):
        self.clear()
        
        self.worker = RenderCacheWorker(timeline, self.cache_dir, preview_scale, processor=processor)
        self.worker.progress_updated.connect(self._on_worker_progress)
        return self.worker

    def _on_worker_progress(self, current, total):
        # We can add the frame to the cached_frames set as it's processed
        if current > 0:
            self.cached_frames.add(current - 1)

    def cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self.worker = None
