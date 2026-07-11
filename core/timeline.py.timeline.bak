from typing import List

from .clip import Clip
from .track import Track


class Timeline:

    def __init__(self):

        self.tracks: List[Track] = [
            Track(
                "Video Track 1",
                "video"
            ),
            Track(
                "Audio Track 1",
                "audio"
            )
        ]

        self.selected_clip: Clip | None = None


    @property
    def clips(self):

        return self.video_tracks[0].clips


    @property
    def video_tracks(self):

        return [
            track
            for track in self.tracks
            if track.track_type == "video"
        ]


    @property
    def audio_tracks(self):

        return [
            track
            for track in self.tracks
            if track.track_type == "audio"
        ]


    def add_clip(self, clip: Clip):

        self.video_tracks[0].add_clip(clip)

        if self.selected_clip is None:

            self.selected_clip = clip


    def remove_clip(self, clip: Clip):

        for track in self.tracks:

            if clip in track.clips:

                track.remove_clip(clip)


        if self.selected_clip == clip:

            self.selected_clip = (
                self.clips[0]
                if self.clips
                else None
            )


    def select_clip(self, clip: Clip):

        if clip in self.clips:

            self.selected_clip = clip


    def get_selected_clip(self):

        return self.selected_clip


    def clear(self):

        for track in self.tracks:

            track.clips.clear()


        self.selected_clip = None


    def __len__(self):

        return len(self.clips)


    def __iter__(self):

        return iter(self.clips)
