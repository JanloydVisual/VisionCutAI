"""
InteractiveMaskWorker
----------------------
Runs SAM/MobileSAM inference for the live object-selection preview on a
background thread, off the Qt UI thread.

Requests are "latest wins": if a new request arrives while one is already
being processed, it replaces whatever was pending, and any result computed
for a now-superseded request is dropped instead of emitted. This guarantees
at most one inference call in flight at a time and keeps the UI thread free
to keep rendering the stroke the user is actively drawing, instead of
freezing for the ~1s a MobileSAM call can take on modest hardware.
"""

import threading

from PyQt6.QtCore import QThread, pyqtSignal


class InteractiveMaskWorker(QThread):
    result_ready = pyqtSignal(object, object)  # alpha (np.ndarray or None), prompts_used

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._pending = None  # (processor, frame, prompts)
        self._wake = threading.Event()
        self._running = True

    def request(self, processor, frame, prompts):
        with self._lock:
            self._pending = (processor, frame, prompts)
        self._wake.set()

    def stop(self):
        self._running = False
        self._wake.set()
        self.wait()

    def run(self):
        while self._running:
            self._wake.wait()
            self._wake.clear()
            if not self._running:
                break

            with self._lock:
                job = self._pending
                self._pending = None
            if job is None:
                continue

            processor, frame, prompts = job
            try:
                # B4 (Magic Mask roadmap): MobileSAM's encoder always resizes
                # internally to a fixed 684x1024 grid regardless of the
                # pre-inference proxy_scale, so the dominant inference cost
                # is roughly constant whether we pre-downscale to "Balanced"
                # or not (measured this session). That makes running the
                # single live-prompt call at "Best" a largely free accuracy
                # win -- more detail survives into the fixed-size encoder
                # input, which matters most for small/thin subjects. This
                # only affects this one interactive call; the offline
                # render-cache pass (many frames, genuinely throughput-
                # sensitive) is unaffected and keeps using the user's chosen
                # quality setting.
                print("[INTERACTIVE MASK WORKER] inference started")
                rgba = processor.process(frame, custom_prompt=prompts, quality_override="Best")
                print("[INTERACTIVE MASK WORKER] inference completed")
                alpha = rgba[:, :, 3]
                print(f"[INTERACTIVE MASK WORKER] mask size: {alpha.shape}")
            except Exception:
                alpha = None

            # If a newer request already landed while we were computing,
            # this result is stale -- drop it and let the loop pick up the
            # latest job on its next pass instead of emitting outdated work.
            with self._lock:
                superseded = self._pending is not None
            if not superseded:
                self.result_ready.emit(alpha, prompts)
