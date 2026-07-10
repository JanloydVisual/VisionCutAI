from dataclasses import dataclass, field
from typing import Any

@dataclass
class Clip:
    source_path: str
    start_frame: int
    end_frame: int
    fps: float
    duration: float

    background_removed: bool = False

    cached_frames: dict[int, Any] = field(default_factory=dict)

    mask = None

    effects: list = field(default_factory=list)

    @property
    def frame_count(self):
        return self.end_frame - self.start_frame + 1
