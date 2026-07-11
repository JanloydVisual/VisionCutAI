from dataclasses import dataclass


@dataclass
class AudioClip:

    source_path: str

    duration: float

    sample_rate: int = 48000

    channels: int = 2

    timeline_start_frame: int = 0

    muted: bool = False
