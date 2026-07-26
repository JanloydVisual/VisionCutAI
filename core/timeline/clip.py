from dataclasses import dataclass, field
from typing import Any


@dataclass
class Clip:

    source_path: str

    # Source media range
    start_frame: int
    end_frame: int

    fps: float
    duration: float

    # Timeline position
    timeline_start_frame: int = 0

    background_removed: bool = False

    # Linked media relationship (video <-> audio)
    linked_id: str | None = None

    cached_frames: dict[int, Any] = field(
        default_factory=dict
    )

    mask = None

    effects: list = field(
        default_factory=list
    )
    
    keyframes: dict = field(
        default_factory=lambda: {
            "opacity": [],
            "blur_amount": [],
            "feather_amount": [],
            "background_settings": []
        }
    )

    @property
    def frame_count(self):

        return (
            self.end_frame
            -
            self.start_frame
            +
            1
        )

    @property
    def timeline_end_frame(self):

        return (
            self.timeline_start_frame
            +
            self.frame_count
            -
            1
        )
