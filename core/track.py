from dataclasses import dataclass, field
from typing import List

from .clip import Clip
from .audio_clip import AudioClip


@dataclass
class Track:

    name: str = "Video Track 1"

    track_type: str = "video"

    clips: List[Clip | AudioClip] = field(
        default_factory=list
    )

    enabled: bool = True

    locked: bool = False


    def add_clip(self, clip: Clip):

        self.clips.append(clip)


    def remove_clip(self, clip: Clip):

        if clip in self.clips:

            self.clips.remove(clip)
