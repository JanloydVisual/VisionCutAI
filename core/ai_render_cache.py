import os
import json
import time
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from dataclasses import asdict

class AIRenderWorker(QThread):
    progress_updated = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(bool, str)         # success, message

    def __init__(self, timeline_playback, tracking_engine, cache_dir: Path, processor=None, parent=None):
        super().__init__(parent)
        self.timeline_playback = timeline_playback
        self.tracking_engine = tracking_engine
        self.cache_dir = cache_dir
        self.processor = processor
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        # Audit 1.0 fix: caps is now created before the try/finally and
        # released in `finally` so an exception mid-loop (frame read,
        # processor error, disk write failure) can't leak open
        # cv2.VideoCapture handles the way it previously could.
        caps = {}
        try:
            if not self.processor:
                self.finished.emit(False, "No AI processor available")
                return

            tracking_cache = self.tracking_engine.tracking_cache
            if not tracking_cache:
                self.finished.emit(True, "Nothing to render")
                return

            # Determine the frames we need to process based on tracking cache bounds
            timeline_frames = []
            
            max_timeline_frame = 0
            for track in self.timeline_playback.timeline.tracks:
                for clip in track.clips:
                    if hasattr(clip, 'end_frame') and clip.timeline_end_frame > max_timeline_frame:
                        max_timeline_frame = clip.timeline_end_frame

            if max_timeline_frame == 0:
                self.finished.emit(True, "Empty timeline")
                return
                
            total_frames = max_timeline_frame + 1

            # To know how many frames actually need rendering
            frames_to_render = []
            for tf in range(total_frames):
                pos = self.timeline_playback.position_at(tf)
                if not pos or not pos.clip:
                    continue
                if pos.source_frame in tracking_cache:
                    frames_to_render.append((tf, pos.source_frame, pos.clip.source_path))
                    
            if not frames_to_render:
                self.finished.emit(True, "No tracked frames to render")
                return
                
            total_render = len(frames_to_render)

            for i, (tf, source_frame, source_path) in enumerate(frames_to_render):
                if self._cancel_requested:
                    self.finished.emit(False, "Cancelled by user")
                    break

                # Check if already cached
                mask_path = self.cache_dir / f"frame_{tf:06d}.png"
                if mask_path.exists():
                    self.progress_updated.emit(i + 1, total_render)
                    continue

                if source_path not in caps:
                    caps[source_path] = cv2.VideoCapture(source_path)

                cap = caps[source_path]
                cap.set(cv2.CAP_PROP_POS_FRAMES, source_frame)
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    state = tracking_cache[source_frame]
                    prompt = self.tracking_engine.object_tracker.get_sam_prompt(state)
                    
                    # Process frame (process returns RGBA)
                    rgba = self.processor.process(frame, custom_prompt=prompt)
                    
                    # Extract 1-channel alpha mask
                    alpha_mask = rgba[:, :, 3]
                    
                    # Save mask
                    cv2.imwrite(str(mask_path), alpha_mask)
                    
                    # Save metadata
                    meta_path = self.cache_dir / f"frame_{tf:06d}.json"
                    metadata = {
                        "frame_number": state.frame_number,
                        "bbox": state.bounding_box,
                        "confidence": state.confidence,
                        "sam_prompt": prompt
                    }
                    with open(meta_path, 'w') as f:
                        json.dump(metadata, f)
                    
                self.progress_updated.emit(i + 1, total_render)
                
                # Render Priority Throttling
                priority = getattr(self, 'render_priority', 'Normal')
                if priority == 'Low':
                    time.sleep(0.1)
                elif priority == 'Normal':
                    time.sleep(0.01)
                # High has no sleep

            if not self._cancel_requested:
                self.finished.emit(True, "Render Cache Complete")

        except Exception as e:
            self.finished.emit(False, str(e))
        finally:
            for cap in caps.values():
                cap.release()

class CacheLookaheadThread(QThread):
    def __init__(self, cache_dir, parent=None):
        super().__init__(parent)
        self.cache_dir = cache_dir
        self.running = True
        self.target_frame = 0
        self.preload_amount = 120
        self.ram_cache = {}

    def set_target(self, frame_num):
        self.target_frame = frame_num
        
    def stop(self):
        self.running = False
        self.wait()

    def run(self):
        import time
        while self.running:
            min_frame = max(0, self.target_frame - 10)
            max_frame = self.target_frame + self.preload_amount
            
            keys_to_remove = [k for k in self.ram_cache.keys() if k < min_frame or k > max_frame]
            for k in keys_to_remove:
                del self.ram_cache[k]
                
            loaded_any = False
            for f in range(self.target_frame, max_frame):
                if not self.running:
                    break
                if f not in self.ram_cache:
                    mask_path = self.cache_dir / f"frame_{f:06d}.png"
                    if mask_path.exists():
                        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                        if mask is not None:
                            self.ram_cache[f] = mask
                            loaded_any = True
            
            if not loaded_any:
                time.sleep(0.05)
            else:
                time.sleep(0.01)


class AIRenderCache(QObject):
    cache_updated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.cache_dir = Path(tempfile.gettempdir()) / "VisionCutAI_Cache"
        self.worker = None
        self.cached_frames = set()
        self.render_priority = 'Normal'

        # Lookahead thread
        self.lookahead = CacheLookaheadThread(self.cache_dir)
        self.lookahead.start()

        self._ensure_dir()

    def _ensure_dir(self):
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True)

    def clear(self):
        """Wipe the cache directory."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir, ignore_errors=True)
        self.cached_frames.clear()
        self.lookahead.ram_cache.clear()
        self._ensure_dir()
        self.cache_updated.emit()
        
    def invalidate_from(self, frame_num: int):
        """Invalidates cache from frame_num onward."""
        # 1. Update set
        self.cached_frames = {f for f in self.cached_frames if f < frame_num}
        
        # 2. Update RAM cache
        keys_to_remove = [k for k in self.lookahead.ram_cache.keys() if k >= frame_num]
        for k in keys_to_remove:
            del self.lookahead.ram_cache[k]
            
        # 3. Delete files from disk
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("frame_*.png"):
                try:
                    num_str = f.stem.split('_')[1]
                    if int(num_str) >= frame_num:
                        f.unlink(missing_ok=True)
                        meta_file = f.with_suffix(".json")
                        meta_file.unlink(missing_ok=True)
                except Exception:
                    pass
        self.cache_updated.emit()

    def has_frame(self, timeline_frame: int) -> bool:
        """Check if a frame exists in the cache."""
        if timeline_frame in self.cached_frames:
            return True
            
        # Also check disk in case it was written but set wasn't updated
        mask_path = self.cache_dir / f"frame_{timeline_frame:06d}.png"
        if mask_path.exists():
            self.cached_frames.add(timeline_frame)
            return True
            
        return False

    def get_mask(self, timeline_frame: int):
        """Read alpha mask from cache. Returns 1-channel numpy array or None."""
        # Tell lookahead thread our current position
        self.lookahead.set_target(timeline_frame)
        
        # Check RAM first
        if timeline_frame in self.lookahead.ram_cache:
            return self.lookahead.ram_cache[timeline_frame]
            
        if not self.has_frame(timeline_frame):
            return None
            
        # Fallback to disk read (missed RAM)
        frame_path = self.cache_dir / f"frame_{timeline_frame:06d}.png"
        if frame_path.exists():
            mask = cv2.imread(str(frame_path), cv2.IMREAD_GRAYSCALE)
            if mask is not None:
                self.lookahead.ram_cache[timeline_frame] = mask
            return mask
        return None
        
    def get_metadata(self, timeline_frame: int) -> dict:
        """Read JSON metadata for a cached frame."""
        meta_path = self.cache_dir / f"frame_{timeline_frame:06d}.json"
        if meta_path.exists():
            try:
                with open(meta_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_composite(self, timeline_frame: int, original_bgr: np.ndarray) -> np.ndarray:
        """
        Takes the original BGR frame, looks up the cached mask, and returns an RGBA composite.
        Returns None if cache is missing.
        """
        mask = self.get_mask(timeline_frame)
        if mask is None:
            return None
            
        h, w = original_bgr.shape[:2]
        mh, mw = mask.shape[:2]
        
        # Ensure dimensions match
        if h != mh or w != mw:
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
            
        rgb = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)
        rgba = np.dstack((rgb, mask))
        return rgba

    def start_caching(self, timeline_playback, tracking_engine, processor=None):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()

        self.worker = AIRenderWorker(timeline_playback, tracking_engine, self.cache_dir, processor=processor)
        self.worker.render_priority = self.render_priority
        self.worker.progress_updated.connect(self._on_worker_progress)
        self.worker.start()
        return self.worker

    def _on_worker_progress(self, current, total):
        self.cache_updated.emit()

    def set_render_priority(self, priority: str):
        """Update the offline render-thread priority (Low/Normal/High).
        Applies to the next render and, if a worker is already running,
        takes effect on its very next frame too."""
        self.render_priority = priority
        if self.worker and self.worker.isRunning():
            self.worker.render_priority = priority

    def cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self.worker = None

    def release(self):
        """Audit 1.0 fix: stop every background thread this object owns.
        Previously nothing called this -- the lookahead thread's own stop()
        (correctly implemented: flag then wait()) had zero call sites
        anywhere, so it ran forever until process exit on every single
        app run, and an in-flight render worker was simply abandoned."""
        self.cancel()
        self.lookahead.stop()
