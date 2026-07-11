"""
Signal
------
Minimal, dependency-free observer/event class. Mirrors the
connect()/emit() shape of pyqtSignal closely enough that engine
code reads the same, but has zero Qt dependency. This is what
makes core/ and ai/ genuinely reusable outside a PyQt6 app - by
a future Flutter bridge, a headless service, or tests.
"""


class Signal:

    def __init__(self):
        self._slots = []

    def connect(self, slot) -> None:
        self._slots.append(slot)

    def disconnect(self, slot) -> None:
        if slot in self._slots:
            self._slots.remove(slot)

    def emit(self, *args, **kwargs) -> None:
        for slot in list(self._slots):
            slot(*args, **kwargs)
