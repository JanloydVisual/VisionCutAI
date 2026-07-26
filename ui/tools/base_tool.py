class BaseToolState:
    """
    Base class for ViewerWidget interaction tools.
    """
    def __init__(self):
        self.viewer = None

    def activate(self, viewer) -> None:
        """Called when the tool becomes active."""
        self.viewer = viewer

    def deactivate(self) -> None:
        """Called when the tool is deactivated."""
        self.viewer = None

    def cancel(self) -> None:
        """Called to abort any ongoing interaction (e.g. on ESC or when losing focus)."""
        pass

    def on_mouse_press(self, event) -> bool:
        """Return True if the event was consumed."""
        return False

    def on_mouse_move(self, event) -> bool:
        """Return True if the event was consumed."""
        return False

    def on_mouse_release(self, event) -> bool:
        """Return True if the event was consumed."""
        return False

    def on_wheel(self, event) -> bool:
        """Return True if the event was consumed."""
        return False

    def on_key_press(self, event) -> bool:
        """Return True if the event was consumed."""
        return False

    def on_key_release(self, event) -> bool:
        """Return True if the event was consumed."""
        return False
