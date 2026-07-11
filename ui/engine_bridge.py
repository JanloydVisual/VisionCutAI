"""
ProcessingBridge
-----------------
The one deliberately Qt-specific adapter in this app. Bridges the
plain, framework-independent core.signals.Signal
(ProcessingEngine.frame_processed), emitted from a background
Python thread, onto a real pyqtSignal delivered safely on the Qt
main/GUI thread.

Qt widgets must only be touched from the main thread - this class
exists specifically so nothing in core/ or ai/ needs to know that
rule, or import PyQt6 at all. A future Flutter frontend would need
its own small equivalent bridge, not a rewrite of ProcessingEngine.
"""

from PyQt6.QtCore import QObject, pyqtSignal


class ProcessingBridge(QObject):

    frame_processed = pyqtSignal(object)

    def __init__(self, processing_engine, parent=None):
        super().__init__(parent)
        processing_engine.frame_processed.connect(self._on_frame_processed)

    def _on_frame_processed(self, frame):
        # Called on ProcessingEngine's background thread. Emitting
        # a real pyqtSignal here is what safely marshals delivery
        # back onto this QObject's own thread (the Qt main thread).
        self.frame_processed.emit(frame)
