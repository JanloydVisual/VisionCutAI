from dataclasses import dataclass

from core.signals import Signal


@dataclass(frozen=True)
class PlaybackPosition:
    timeline_frame: int
    source_frame: int
    clip: object


class TimelinePlayback:
    """
    Timeline-frame mapper and playback coordinator.

    This class does not modify VideoEngine. For now it accepts any
    decoder exposing seek(frame_index) and read(), which makes it
    testable with a fake decoder before integration.
    """

    def __init__(self, timeline, decoder=None):
        self.timeline = timeline
        self.decoder = decoder
        self.current_timeline_frame = 0
        self.frame_ready = Signal()

    def _ordered_clips(self):
        return sorted(
            self.timeline.clips,
            key=lambda clip: clip.timeline_start_frame,
        )

    def position_at(self, timeline_frame):
        timeline_frame = max(0, int(timeline_frame))

        for clip in self._ordered_clips():
            if clip.timeline_start_frame <= timeline_frame <= clip.timeline_end_frame:
                return PlaybackPosition(
                    timeline_frame=timeline_frame,
                    source_frame=(
                        clip.start_frame
                        + timeline_frame
                        - clip.timeline_start_frame
                    ),
                    clip=clip,
                )

        return None

    def next_playable_frame(self, timeline_frame):
        timeline_frame = max(0, int(timeline_frame))

        position = self.position_at(timeline_frame)
        if position is not None:
            return timeline_frame

        for clip in self._ordered_clips():
            if clip.timeline_end_frame >= timeline_frame:
                return max(timeline_frame, clip.timeline_start_frame)

        return None

    def seek(self, timeline_frame):
        playable_frame = self.next_playable_frame(timeline_frame)
        if playable_frame is None:
            return None

        position = self.position_at(playable_frame)
        if position is None:
            return None

        self.current_timeline_frame = position.timeline_frame

        if self.decoder is not None:
            self.decoder.seek(position.source_frame)
            frame = self.decoder.read()
            self.frame_ready.emit(frame, position.timeline_frame)

        return position

    def step_forward(self):
        return self.seek(self.current_timeline_frame + 1)
