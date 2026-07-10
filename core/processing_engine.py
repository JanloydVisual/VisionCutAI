"""
ProcessingEngine
----------------
Reusable, UI-independent frame processing pipeline.

Receives raw frames (from VideoEngine.frame_ready), pushes them
through a pluggable FrameProcessor, and emits the result via a Qt
signal. Intended to run on a background QThread so processing
never blocks the UI event loop.

Uses a bounded queue with a "latest frame wins" strategy: if
frames arrive faster than they can be processed, older pending
frames are dropped rather than building an ever-growing backlog.
This keeps real-time preview latency low and is the standard
approach for real-time video pipelines under backpressure.

Has ZERO knowledge of VideoEngine, VideoPlayerWidget, VideoPreview,
or any other UI component - only frames and a FrameProcessor.
"""

from collections import deque
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from core.frame_processor import FrameProcessor, PassthroughProcessor


class ProcessingEngine(QObject):

    frame_processed = pyqtSignal(object)

    def __init__(self, processor: FrameProcessor = None, max_queue_size: int = 2):
        super().__init__()

        self._processor = processor or PassthroughProcessor()
        self._queue = deque(maxlen=max_queue_size)
        self._busy = False

    def set_processor(self, processor: FrameProcessor) -> None:
        """
        Swaps the active processor at runtime. This is the single
        plug-in point future AI models attach to - nothing else in
        this class, or anywhere upstream/downstream, needs to change.
        """
        self._processor = processor

    def enqueue_frame(self, frame) -> None:
        """
        Slot: receives a raw frame. Safe to call via a cross-thread
        signal connection - Qt automatically delivers it as a
        queued call when emitter and receiver live on different
        threads.
        """
        self._queue.append(frame)

        if not self._busy:
            # Defer instead of processing inline, so a burst of
            # enqueue_frame calls can't stack up synchronously or
            # block whatever called this slot.
            QTimer.singleShot(0, self._process_next)

    def _process_next(self) -> None:
        if not self._queue:
            self._busy = False
            return

        self._busy = True

        # Always process the newest frame; discard anything older
        # that piled up behind it.
        frame = self._queue[-1]
        self._queue.clear()

        try:
            processed = self._processor.process(frame)
        except Exception:
            # A misbehaving processor must never break playback.
            processed = frame

        self.frame_processed.emit(processed)

        if self._queue:
            QTimer.singleShot(0, self._process_next)
        else:
            self._busy = False
