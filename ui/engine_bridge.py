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
    """
    Bridges pure Python core.ProcessingEngine to PyQt6 signals,
    allowing the worker thread to safely send Qt signals to the main thread.
    """
    frame_processed = pyqtSignal(object)
    telemetry_updated = pyqtSignal(object)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.engine.frame_processed.connect(self._on_frame_processed)
        self.engine.telemetry_updated.connect(self._on_telemetry_updated)

    def _on_frame_processed(self, frame):
        self.frame_processed.emit(frame)

    def _on_telemetry_updated(self, data):
        self.telemetry_updated.emit(data)
