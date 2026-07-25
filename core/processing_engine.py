"""
ProcessingEngine
----------------
Reusable, UI-independent frame processing pipeline. Pure Python -
no Qt dependency at all, so this class (and any FrameProcessor it
drives) can be reused unchanged by any future frontend or service,
not just PyQt6.

Runs its own background thread (plain threading.Thread) so
processing never blocks whichever thread calls enqueue_frame().
Uses a bounded queue.Queue with "latest frame wins" semantics -
same real-time-pipeline behavior as before, now framework-free.
"""

import threading
import queue
import time
import logging

from core.frame_processor import FrameProcessor, PassthroughProcessor
from core.signals import Signal

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ProcessingEngine:

    def __init__(self, processor: FrameProcessor = None, max_queue_size: int = 2):

        self.frame_processed = Signal()
        self.telemetry_updated = Signal()

        self._processor = processor or PassthroughProcessor()
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._thread = None
        
        self._dropped_frames = 0
        self._processed_frames = 0
        self._last_log_time = time.time()

    def set_processor(self, processor: FrameProcessor) -> None:
        self._processor = processor

    def set_quality(self, quality: str) -> None:
        """Forward AI quality settings down to the processor."""
        if hasattr(self._processor, 'set_quality'):
            self._processor.set_quality(quality)

    def start(self) -> None:
        """Starts the background worker thread. Safe to call once."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        # Drain the queue to ensure a fresh start
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._dropped_frames = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_model(self, model_name: str):
        if hasattr(self._processor, 'set_model'):
            self._processor.set_model(model_name)

    def stop(self) -> None:
        """Signals the worker thread to stop and waits for it to exit."""
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def enqueue_frame(self, frame) -> None:
        """
        Called from the producing thread (VideoEngine, on the main
        thread today). Keeps only the newest frame - if the queue
        is full, the oldest pending frame is dropped.
        """
        try:
            self._queue.put_nowait(frame)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._dropped_frames += 1
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(frame)
            except queue.Full:
                pass

    def _run(self) -> None:

        while not self._stop_event.is_set():

            frame = self._queue.get()

            if frame is None:
                continue

            # Drain to the newest frame if more piled up while busy.
            while True:
                try:
                    newer = self._queue.get_nowait()
                    if newer is not None:
                        frame = newer
                        self._dropped_frames += 1
                except queue.Empty:
                    break

            start_time = time.perf_counter()
            try:
                processor = self._processor
                if processor:
                    processed = processor.process(frame)
                else:
                    processed = frame
            except Exception as e:
                logger.error(f"Processing failed: {e}", exc_info=True)
                processed = frame
            latency_ms = (time.perf_counter() - start_time) * 1000

            self._processed_frames += 1
            now = time.time()
            if now - self._last_log_time >= 5.0:
                fps = self._processed_frames / (now - self._last_log_time)
                h, w = frame.shape[:2]
                logger.info(f"AI Engine | Source Frame: {w}x{h} | Latency: {latency_ms:.1f}ms | "
                            f"Processed FPS: {fps:.1f} | Dropped Frames: {self._dropped_frames}")
                
                self._processed_frames = 0
                self._dropped_frames = 0
                self._last_log_time = now

            self.telemetry_updated.emit({"latency_ms": latency_ms})
            self.frame_processed.emit(processed)
