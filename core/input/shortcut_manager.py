class ShortcutManager:
    """
    Centralized repository for keyboard shortcuts and their descriptions.
    """
    SHORTCUTS = {
        "Space": "Play / Pause",
        "Ctrl+Z": "Undo active object",
        "Ctrl+Shift+Z": "Redo active object",
        "B": "Brush Tool",
        "R": "Rectangle Tool",
        "P": "Point Tool",
        "[": "Previous anchor",
        "]": "Next anchor"
    }
    
    @classmethod
    def get_all(cls):
        return cls.SHORTCUTS
        
    @classmethod
    def get_shortcuts(cls):
        return [
            {"key": "Space", "description": "Play / Pause"},
            {"key": "Ctrl+Z", "description": "Undo active object"},
            {"key": "Ctrl+Shift+Z", "description": "Redo active object"},
            {"key": "[", "description": "Previous anchor"},
            {"key": "]", "description": "Next anchor"}
        ]
