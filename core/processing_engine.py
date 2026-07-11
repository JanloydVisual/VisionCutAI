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

from core.frame_processor import FrameProcessor, PassthroughProcessor
from core.signals import Signal


class ProcessingEngine:

    def __init__(self, processor: FrameProcessor = None, max_queue_size: int = 2):

        self.frame_processed = Signal()

        self._processor = processor or PassthroughProcessor()
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._thread = None

    def set_processor(self, processor: FrameProcessor) -> None:
        self._processor = processor

    def start(self) -> None:
        """Starts the background worker thread. Safe to call once."""
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

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
                except queue.Empty:
                    break

            try:
                processed = self._processor.process(frame)
            except Exception:
                processed = frame

            self.frame_processed.emit(processed)
