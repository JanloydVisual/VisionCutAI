from typing import List
from .clip import Clip

class Timeline:

    def __init__(self):

        self.clips: List[Clip] = []

    def add_clip(self, clip: Clip):

        self.clips.append(clip)

    def remove_clip(self, clip: Clip):

        self.clips.remove(clip)

    def clear(self):

        self.clips.clear()

    def __len__(self):

        return len(self.clips)

    def __iter__(self):

        return iter(self.clips)
