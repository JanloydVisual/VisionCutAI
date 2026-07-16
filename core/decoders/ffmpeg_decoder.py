import os
import subprocess
import threading
import time
import queue
import cv2
import numpy as np
import socket

from .base_decoder import IVideoDecoder


class FFmpegNVDECDecoder(IVideoDecoder):
    """
    Hardware-accelerated decoder using FFmpeg NVDEC subprocess via fast TCP IPC.
    Uses a daemon thread to prefetch frames into a queue.
    """

    def __init__(self):
        self._filepath = None
        self._fps = 30.0
        self._total_frames = 0
        self._width = 0
        self._height = 0
        
        self._proc = None
        self._server = None
        self._conn = None
        self._frame_size = 0
        
        # Buffer for recv_into
        self._buf = None
        self._view = None
        
        self._daemon_frame_index = -1
        self._ui_frame_index = -1
        self._target_frame_index = -1
        
        self._queue = queue.Queue(maxsize=15)
        self._thread = None
        self._stop_event = threading.Event()
        
        self._lock = threading.Lock()
        
        # Diagnostics
        self._decode_times = []

    @property
    def name(self) -> str:
        return "FFmpeg NVDEC (GPU)"

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def load(self, filepath: str) -> bool:
        self.release()
        self._filepath = filepath
        
        # Probe metadata quickly
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return False
            
        self._fps = cap.get(cv2.CAP_PROP_FPS)
        if self._fps <= 1:
            self._fps = 30.0
            
        self._total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        self._frame_size = self._width * self._height * 3  # bgr24
        self._buf = bytearray(self._frame_size)
        self._view = memoryview(self._buf)
        
        self._daemon_frame_index = -1
        self._ui_frame_index = -1
        self._target_frame_index = 0
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._reader_thread, daemon=True)
        self._thread.start()
        
        return True

    def _start_subprocess(self, start_frame: int):
        self._kill_subprocess()
        
        start_time_sec = max(0, start_frame) / self._fps
        
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(('127.0.0.1', 0))
        self._server.listen(1)
        self._server.settimeout(2.0)
        port = self._server.getsockname()[1]
        
        cmd = [
            'ffmpeg',
            '-hwaccel', 'cuda',
            '-ss', str(start_time_sec),
            '-i', self._filepath,
            '-f', 'image2pipe',
            '-pix_fmt', 'bgr24',
            '-vcodec', 'rawvideo',
            '-an', '-sn', '-dn',
            '-loglevel', 'error',
            f'tcp://127.0.0.1:{port}'
        ]
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        self._proc = subprocess.Popen(
            cmd,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )
        
        try:
            self._conn, _ = self._server.accept()
            self._conn.settimeout(2.0)
        except socket.timeout:
            pass
            
        self._daemon_frame_index = start_frame - 1

    def _kill_subprocess(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
            self._server = None
        if self._proc:
            try:
                self._proc.kill()
                self._proc.wait(timeout=1)
            except Exception:
                pass
            self._proc = None

    def _read_exact(self) -> bool:
        if not self._conn:
            return False
            
        pos = 0
        while pos < self._frame_size:
            if self._stop_event.is_set():
                return False
            try:
                chunk = self._conn.recv_into(self._view[pos:])
                if not chunk:
                    return False
                pos += chunk
            except Exception:
                return False
        return True

    def _flush_queue(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _reader_thread(self):
        """Background thread that reads frames and queues them."""
        while not self._stop_event.is_set():
            with self._lock:
                target = self._target_frame_index
                current = self._daemon_frame_index

            if target == -1:
                time.sleep(0.01)
                continue

            # Need a restart or far seek?
            if target != -2 and (target < current or target > current + 30):
                with self._lock:
                    self._start_subprocess(target)
                    self._flush_queue()
                    self._daemon_frame_index = target - 1
                continue

            # Initial start?
            if current == -1 and self._proc is None:
                with self._lock:
                    self._start_subprocess(target if target != -2 else 0)
                    self._flush_queue()
                    self._daemon_frame_index = -1
                continue

            # Fast forward? (skip small forwards by dropping)
            if current + 1 < target:
                self._read_exact()
                with self._lock:
                    self._daemon_frame_index += 1
                continue
                
            # Normal sequential read
            if current + 1 == target or target == -2:
                if not self._read_exact():
                    time.sleep(0.01)
                    continue
                    
                frame = np.frombuffer(self._buf, dtype=np.uint8).reshape((self._height, self._width, 3)).copy()
                with self._lock:
                    self._daemon_frame_index += 1
                
                # Retry putting into queue until successful or stopped
                while not self._stop_event.is_set():
                    try:
                        self._queue.put(frame, timeout=0.1)
                        with self._lock:
                            if target != -2:
                                self._target_frame_index = -2
                        break
                    except queue.Full:
                        # Queue is full, meaning the UI is paused or slow. 
                        # We must NOT discard the frame or we lose sync.
                        
                        # If a new target was set while we were waiting, break out so we can seek
                        with self._lock:
                            if self._target_frame_index != target and self._target_frame_index != -2:
                                break
                        continue
            else:
                time.sleep(0.01)

    def read_frame(self, frame_index: int) -> tuple[bool, np.ndarray | None]:
        with self._lock:
            # Tell the thread we want this frame if it's not sequential
            if frame_index != self._ui_frame_index + 1 and self._target_frame_index != frame_index:
                self._target_frame_index = frame_index
                self._flush_queue()
        
        t0 = time.perf_counter()
        
        # Wait for frame
        try:
            frame = self._queue.get(timeout=2.0)
            
            t1 = time.perf_counter()
            latency = (t1 - t0) * 1000
            self._decode_times.append(latency)
            if len(self._decode_times) > 30:
                self._decode_times.pop(0)
                
            self._ui_frame_index = frame_index
            return True, frame
        except queue.Empty:
            return False, None

    def seek(self, frame_index: int) -> bool:
        with self._lock:
            if self._target_frame_index != frame_index:
                self._target_frame_index = frame_index
                self._flush_queue()
        return True

    def release(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        with self._lock:
            self._kill_subprocess()
            self._flush_queue()

    def get_diagnostics(self) -> dict:
        avg_latency = sum(self._decode_times) / max(1, len(self._decode_times)) if self._decode_times else 0
        return {
            "decode_latency_ms": round(avg_latency, 2),
            "fps": round(1000 / avg_latency, 1) if avg_latency > 0 else 0,
            "queue_depth": self._queue.qsize()
        }
