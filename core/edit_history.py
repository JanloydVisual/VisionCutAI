class EditHistory:
    """
    Generic snapshot history.

    A target object must provide snapshot() and restore(snapshot).
    Timeline snapshot/restore integration is added in the next step.
    """

    def __init__(self):
        self._undo_stack = []
        self._redo_stack = []

    @property
    def can_undo(self):
        return bool(self._undo_stack)

    @property
    def can_redo(self):
        return bool(self._redo_stack)

    def record(self, before, after):
        if before == after:
            return False

        self._undo_stack.append((before, after))
        self._redo_stack.clear()
        return True

    def execute(self, target, action):
        before = target.snapshot()
        changed = action()

        if not changed:
            return False

        after = target.snapshot()
        return self.record(before, after)

    def undo(self, target):
        if not self._undo_stack:
            return False

        before, after = self._undo_stack.pop()
        target.restore(before)
        self._redo_stack.append((before, after))
        return True

    def redo(self, target):
        if not self._redo_stack:
            return False

        before, after = self._redo_stack.pop()
        target.restore(after)
        self._undo_stack.append((before, after))
        return True
