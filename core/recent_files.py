"""
Recent Files Manager
--------------------
Manages recently opened files for both images and videos.
"""

import os
from PyQt6.QtCore import QSettings


class RecentFilesManager:
    """Manages recently opened file history."""

    MAX_RECENT_FILES = 10

    def __init__(self):
        self.settings = QSettings("VisionCutAI", "VisionCutAI")

    def add_file(self, filepath: str):
        """Add a file to the recent files list."""
        if not filepath or not os.path.exists(filepath):
            return

        # Get current recent files
        recent_files = self.get_recent_files()

        # Remove if already exists (to move to top)
        if filepath in recent_files:
            recent_files.remove(filepath)

        # Add to beginning
        recent_files.insert(0, filepath)

        # Trim to max
        recent_files = recent_files[:self.MAX_RECENT_FILES]

        # Save
        self.settings.setValue("recent_files", recent_files)

    def get_recent_files(self) -> list:
        """Get list of recent files."""
        return self.settings.value("recent_files", [], type=list)

    def clear(self):
        """Clear recent files list."""
        self.settings.remove("recent_files")

    def remove_file(self, filepath: str):
        """Remove a file from recent files."""
        recent_files = self.get_recent_files()
        if filepath in recent_files:
            recent_files.remove(filepath)
            self.settings.setValue("recent_files", recent_files)