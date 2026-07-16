
from dataclasses import dataclass


@dataclass
class AudioClip:

    source_path: str

    duration: float

    fps: float = 30.0

    sample_rate: int = 48000

    channels: int = 2

    timeline_start_frame: int = 0

    muted: bool = False

    # Linked media relationship (audio <-> video)
    linked_id: str | None = None


    @property
    def frame_count(self):
        return int(self.duration * self.fps)


    @property
    def timeline_end_frame(self):
        return (
            self.timeline_start_frame
            + self.frame_count
            - 1
        )
