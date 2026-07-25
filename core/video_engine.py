import logging
from PyQt6.QtCore import QTimer

from core.signals import Signal
from core.decoders import OpenCVDecoder, FFmpegNVDECDecoder

logger = logging.getLogger(__name__)


class VideoEngine:
    """
    Handles video playback.
    Event system (frame_ready/video_loaded/playback_finished) uses plain Signals.
    """

    def __init__(self):
        self.frame_ready = Signal()
        self.video_loaded = Signal()
        self.playback_finished = Signal()

        self.decoder = None

        self.timer = QTimer()
        self.timer.timeout.connect(self._next_frame)

        self.is_loaded = False
        self.is_playing = False

        self.fps = 30
        self.total_frames = 0
        self.current_frame_index = 0

        self._frame_cache = {}
        self._cache_max_size = 60
        self._last_requested_index = -1

    def _add_to_cache(self, index, frame):
        self._frame_cache[index] = frame
        while len(self._frame_cache) > self._cache_max_size:
            del self._frame_cache[next(iter(self._frame_cache))]

    def load_video(self, filepath):
        if self.decoder:
            self.pause()
            self.decoder.release()
            self.decoder = None

        self._frame_cache.clear()
        self._last_requested_index = -1

        # Try FFmpeg NVDEC first
        try:
            decoder = FFmpegNVDECDecoder()
            if decoder.load(filepath):
                self.decoder = decoder
                logger.info(f"Loaded video using {decoder.name}")
        except Exception as e:
            logger.warning(f"FFmpeg NVDEC failed: {e}. Falling back to OpenCV.")
            self.decoder = None

        # Fallback to OpenCV
        if not self.decoder:
            self.decoder = OpenCVDecoder()
            if not self.decoder.load(filepath):
                self.decoder = None
                return False
            logger.info(f"Loaded video using {self.decoder.name}")

        self.fps = self.decoder.fps
        self.total_frames = self.decoder.total_frames

        self.timer.setInterval(int(1000 / self.fps))
        self.is_loaded = True

        info = {
            "Width": self.decoder.width,
            "Height": self.decoder.height,
            "FPS": self.fps,
            "Frames": self.total_frames,
        }
        self.video_loaded.emit(info)
        self._seek_and_show(0)
        return True

    def play(self):
        if not self.is_loaded:
            return
        self.is_playing = True
        self.timer.start()

    def pause(self):
        self.is_playing = False
        self.timer.stop()

    def stop(self):
        if not self.is_loaded:
            return
        self.pause()
        self._seek_and_show(0)

    def next_frame(self):
        if not self.is_loaded:
            return
        self.pause()
        target = min(self.current_frame_index + 1, self.total_frames - 1)
        self._seek_and_show(target)

    def previous_frame(self):
        if not self.is_loaded:
            return
        self.pause()
        target = max(self.current_frame_index - 1, 0)
        self._seek_and_show(target)

    def seek(self, frame_index):
        if not self.is_loaded:
            return
        self.pause()
        target = max(0, min(frame_index, self.total_frames - 1))
        self._seek_and_show(target)
        
    def get_frame(self, frame_index):
        """Synchronously fetch a frame by index (checks cache first)."""
        if not self.decoder:
            return None
        if frame_index in self._frame_cache:
            return self._frame_cache[frame_index]
        success, frame = self.decoder.read_frame(frame_index)
        if success and frame is not None:
            self._add_to_cache(frame_index, frame)
            return frame
        return None

    def _seek_and_show(self, frame_index):
        if not self.decoder:
            return

        # 1. Check cache
        if frame_index in self._frame_cache:
            frame = self._frame_cache[frame_index]
            self.current_frame_index = frame_index
            self._last_requested_index = frame_index
            self.frame_ready.emit(frame)
            return

        # 2. Detect backward playback
        # Allow a small gap to still trigger buffering, e.g. -1, -2, -4 for fast reverse
        is_playing_backward = False
        if self._last_requested_index != -1 and frame_index < self._last_requested_index:
            gap = self._last_requested_index - frame_index
            if gap <= 8:  # 8x speed max
                is_playing_backward = True

        if is_playing_backward:
            buffer_start = max(0, frame_index - 30)
            buffer_end = frame_index
            
            # Reposition the decoder
            self.decoder.seek(buffer_start)
            
            # Fetch block of frames sequentially
            for i in range(buffer_start, buffer_end + 1):
                success, f = self.decoder.read_frame(i)
                if success and f is not None:
                    self._add_to_cache(i, f)
            
            if frame_index in self._frame_cache:
                frame = self._frame_cache[frame_index]
                self.current_frame_index = frame_index
                self._last_requested_index = frame_index
                self.frame_ready.emit(frame)
                return

        # 3. Normal forward or random seek
        success, frame = self.decoder.read_frame(frame_index)

        if success and frame is not None:
            self._add_to_cache(frame_index, frame)
            self.current_frame_index = frame_index
            self._last_requested_index = frame_index
            self.frame_ready.emit(frame)

    def _next_frame(self):
        if not self.decoder:
            return

        target_index = self.current_frame_index + 1
        
        if target_index in self._frame_cache:
            frame = self._frame_cache[target_index]
            self.current_frame_index = target_index
            self._last_requested_index = target_index
            self.frame_ready.emit(frame)
            return

        success, frame = self.decoder.read_frame(target_index)

        if not success or frame is None:
            self.stop()
            self.playback_finished.emit()
            return

        self._add_to_cache(target_index, frame)
        self.current_frame_index = target_index
        self._last_requested_index = target_index
        self.frame_ready.emit(frame)

    def release(self):
        self.pause()
        if self.decoder:
            self.decoder.release()
            self.decoder = None
        self._frame_cache.clear()
        self.is_loaded = False
        self.is_playing = False
