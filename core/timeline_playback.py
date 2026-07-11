"""
TimelinePlayback
----------------
Timeline-frame coordinator that sits between the controller and
VideoEngine.  It owns the playback clock (QTimer), maps timeline
frames to source frames via the Timeline, and re-emits frames with
timeline-frame metadata so the UI can display the correct position
after edits (trim, split, move, delete).

Signal flow
-----------
    VideoEngine.frame_ready
            |
            +---> ProcessingEngine (background removal, unchanged)
            |
            +---> TimelinePlayback._on_decoder_frame
                      |
                      +---> TimelinePlayback.frame_ready(frame, timeline_frame)
                                |
                                +---> MainWindow.update_preview

TimelinePlayback does NOT touch the AI / background-removal pipeline.
"""

from dataclasses import dataclass

from PyQt6.QtCore import QTimer

from core.signals import Signal


@dataclass(frozen=True)
class PlaybackPosition:
    timeline_frame: int
    source_frame: int
    clip: object


class TimelinePlayback:
    """
    Timeline-frame mapper and playback coordinator.

    Wraps a decoder (VideoEngine) and a Timeline to present a
    timeline-frame-oriented interface to the rest of the app.
    """

    def __init__(self, timeline, decoder=None):
        self.timeline = timeline
        self.decoder = decoder
        self.current_timeline_frame = 0
        self.is_playing = False

        # Signal: emits (frame: np.ndarray, timeline_frame: int)
        self.frame_ready = Signal()

        self._play_direction = 1
        self._timer = None

        if decoder is not None:
            self._connect_decoder(decoder)

    # ------------------------------------------------------------------
    # Decoder wiring
    # ------------------------------------------------------------------

    def set_decoder(self, decoder) -> None:
        """Attach (or swap) the decoder and wire its frame_ready signal."""
        self.decoder = decoder
        self._connect_decoder(decoder)

    def _connect_decoder(self, decoder) -> None:
        if hasattr(decoder, "frame_ready"):
            decoder.frame_ready.connect(self._on_decoder_frame)

    def _on_decoder_frame(self, frame) -> None:
        """Re-emit the frame with the current timeline position."""
        self.frame_ready.emit(frame, self.current_timeline_frame)

    # ------------------------------------------------------------------
    # Ordered clips helper
    # ------------------------------------------------------------------

    def _ordered_clips(self):
        return sorted(
            self.timeline.clips,
            key=lambda clip: clip.timeline_start_frame,
        )

    # ------------------------------------------------------------------
    # Frame mapping
    # ------------------------------------------------------------------

    def position_at(self, timeline_frame):
        """Return a PlaybackPosition for *timeline_frame* or None."""
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
        """Return the next timeline frame that has clip content."""
        timeline_frame = max(0, int(timeline_frame))

        position = self.position_at(timeline_frame)
        if position is not None:
            return timeline_frame

        for clip in self._ordered_clips():
            if clip.timeline_end_frame >= timeline_frame:
                return max(timeline_frame, clip.timeline_start_frame)

        return None

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    def _get_fps(self) -> float:
        clips = self.timeline.clips
        if clips:
            return clips[0].fps
        return 30.0

    def _ensure_timer(self) -> QTimer:
        if self._timer is None:
            self._timer = QTimer()
            self._timer.timeout.connect(self._tick)
        return self._timer

    def toggle_playback(self) -> None:
        """Toggle between play and pause. Starts from current position."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        """Start forward playback from the current timeline position."""
        if not self.decoder or not self.decoder.is_loaded:
            return
        self._play_direction = 1
        timer = self._ensure_timer()
        timer.setInterval(int(1000 / self._get_fps()))
        self.is_playing = True
        timer.start()

    def play_reverse(self) -> None:
        """Start reverse playback from the current timeline position."""
        if not self.decoder or not self.decoder.is_loaded:
            return
        self._play_direction = -1
        timer = self._ensure_timer()
        timer.setInterval(int(1000 / self._get_fps()))
        self.is_playing = True
        timer.start()

    def pause(self) -> None:
        """Pause playback."""
        self.is_playing = False
        if self._timer is not None:
            self._timer.stop()

    def stop(self) -> None:
        """Stop and return to the first playable frame."""
        self.pause()
        self.seek(0)

    def _tick(self) -> None:
        """Timer callback – advance one timeline frame in the current direction."""
        next_frame = self.current_timeline_frame + self._play_direction
        position = self.seek(next_frame)
        if position is None:
            self.pause()

    # ------------------------------------------------------------------
    # Seeking
    # ------------------------------------------------------------------

    def seek(self, timeline_frame):
        """
        Seek to *timeline_frame*.

        Maps to the correct source frame, tells the decoder to seek
        there, and returns a PlaybackPosition (or None if no clip
        covers that frame).
        """
        playable_frame = self.next_playable_frame(timeline_frame)
        if playable_frame is None:
            return None

        position = self.position_at(playable_frame)
        if position is None:
            return None

        self.current_timeline_frame = position.timeline_frame

        if self.decoder is not None:
            self.decoder.seek(position.source_frame)

        return position

    def step_forward(self):
        """Advance by one timeline frame."""
        return self.seek(self.current_timeline_frame + 1)

    def step_backward(self):
        """Go back by one timeline frame."""
        return self.seek(self.current_timeline_frame - 1)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def release(self) -> None:
        self.pause()
        self._timer = None
        self.decoder = None