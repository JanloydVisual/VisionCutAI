from dataclasses import dataclass


@dataclass
class TimelineClip:

    name: str

    start_frame: int

    end_frame: int

    selected: bool = False
