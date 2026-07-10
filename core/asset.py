from dataclasses import dataclass
from pathlib import Path

@dataclass
class Asset:
    id: str
    filepath: str
    media_type: str

    width: int = 0
    height: int = 0
    fps: float = 0.0
    duration: float = 0.0
    frame_count: int = 0

    @property
    def filename(self):
        return Path(self.filepath).name

    @property
    def resolution(self):
        return f"{self.width}x{self.height}"
