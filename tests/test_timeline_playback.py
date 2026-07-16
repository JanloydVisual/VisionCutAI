import unittest

from core.clip import Clip
from core.edit_history import EditHistory
from core.signals import Signal
from core.timeline import Timeline
from core.timeline_playback import TimelinePlayback, PlaybackPosition


class FakeDecoder:
    def __init__(self):
        self.seek_calls = []
        self.current_frame = None
        self.is_loaded = True
        self.frame_ready = Signal()

    def seek(self, frame_index):
        self.current_frame = frame_index
        self.seek_calls.append(frame_index)

    def read(self):
        return {"source_frame": self.current_frame}


def clip(start, end, timeline_start=0):
    return Clip(
        source_path="video.mp4",
        start_frame=start,
        end_frame=end,
        fps=30.0,
        duration=(end - start + 1) / 30.0,
        timeline_start_frame=timeline_start,
    )


class SnapshotTarget:
    def __init__(self):
        self.value = 0

    def snapshot(self):
        return {"value": self.value}

    def restore(self, snapshot):
        self.value = snapshot["value"]


class TimelinePlaybackTests(unittest.TestCase):
    def test_normal_playback_maps_timeline_to_source_frames(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        position = playback.seek(4)

        self.assertEqual(position.source_frame, 4)
        self.assertEqual(decoder.seek_calls, [4])
        self.assertEqual(playback.current_timeline_frame, 4)

    def test_split_clips_play_as_independent_sections(self):
        timeline = Timeline()
        left = clip(0, 4, 0)
        right = clip(5, 9, 5)
        timeline.add_clip(left)
        timeline.add_clip(right)
        playback = TimelinePlayback(timeline)

        self.assertEqual(playback.position_at(4).source_frame, 4)
        self.assertEqual(playback.position_at(5).source_frame, 5)
        self.assertIs(playback.position_at(5).clip, right)

    def test_trimmed_clip_respects_source_and_timeline_boundaries(self):
        timeline = Timeline()
        trimmed = clip(3, 7, 3)
        timeline.add_clip(trimmed)
        playback = TimelinePlayback(timeline)

        self.assertIsNone(playback.position_at(2))
        self.assertEqual(playback.position_at(3).source_frame, 3)
        self.assertEqual(playback.position_at(7).source_frame, 7)
        self.assertIsNone(playback.position_at(8))

    def test_deleted_clip_gap_is_skipped(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 2, 0))
        timeline.add_clip(clip(6, 8, 6))
        playback = TimelinePlayback(timeline)

        self.assertEqual(playback.next_playable_frame(3), 6)
        self.assertEqual(playback.seek(3).timeline_frame, 6)
        self.assertEqual(playback.seek(3).source_frame, 6)

    def test_moved_clip_uses_its_new_timeline_position(self):
        timeline = Timeline()
        moved = clip(0, 4, 10)
        timeline.add_clip(moved)
        playback = TimelinePlayback(timeline)

        self.assertIsNone(playback.position_at(9))
        self.assertEqual(playback.position_at(10).source_frame, 0)
        self.assertEqual(playback.position_at(14).source_frame, 4)

    def test_undo_and_redo_restore_snapshots(self):
        target = SnapshotTarget()
        history = EditHistory()

        self.assertTrue(history.execute(
            target,
            lambda: setattr(target, "value", 5) is None,
        ))
        self.assertEqual(target.value, 5)

        self.assertTrue(history.undo(target))
        self.assertEqual(target.value, 0)

        self.assertTrue(history.redo(target))
        self.assertEqual(target.value, 5)

    # ------------------------------------------------------------------
    # Coordinator tests
    # ------------------------------------------------------------------

    def test_seek_outside_clips_returns_none(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 4, 0))
        playback = TimelinePlayback(timeline)

        self.assertIsNone(playback.seek(10))

    def test_seek_negative_frame_clamps_to_zero(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        position = playback.seek(-5)
        self.assertEqual(position.timeline_frame, 0)
        self.assertEqual(position.source_frame, 0)

    def test_step_forward_advances_timeline_frame(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.seek(3)
        position = playback.step_forward()
        self.assertEqual(position.timeline_frame, 4)
        self.assertEqual(position.source_frame, 4)

    def test_step_backward_retreats_timeline_frame(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.seek(5)
        position = playback.step_backward()
        self.assertEqual(position.timeline_frame, 4)
        self.assertEqual(position.source_frame, 4)

    def test_step_forward_at_end_returns_none(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 2, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.seek(2)
        self.assertIsNone(playback.step_forward())

    def test_step_backward_at_start_clamps_to_zero(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 2, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.seek(0)
        position = playback.step_backward()
        self.assertEqual(position.timeline_frame, 0)
        self.assertEqual(position.source_frame, 0)

    def test_play_pause_stop_controls_state(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        self.assertFalse(playback.is_playing)

        playback.play()
        self.assertTrue(playback.is_playing)

        playback.pause()
        self.assertFalse(playback.is_playing)

        playback.play()
        self.assertTrue(playback.is_playing)

        playback.stop()
        self.assertFalse(playback.is_playing)
        self.assertEqual(playback.current_timeline_frame, 0)

    def test_stop_returns_to_first_playable_frame(self):
        timeline = Timeline()
        timeline.add_clip(clip(5, 9, 10))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.seek(12)
        playback.stop()
        self.assertEqual(playback.current_timeline_frame, 10)

    def test_frame_ready_signal_emits_with_timeline_frame(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        received = []
        playback.frame_ready.connect(lambda f, tf: received.append((f, tf)))
        decoder.frame_ready.emit("frame_data")

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], ("frame_data", 0))

    def test_frame_ready_signal_after_seek(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        received = []
        playback.frame_ready.connect(lambda f, tf: received.append((f, tf)))

        playback.seek(5)
        decoder.frame_ready.emit("frame_after_seek")

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], ("frame_after_seek", 5))

    def test_set_decoder_wires_new_decoder(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        playback = TimelinePlayback(timeline)

        decoder = FakeDecoder()
        playback.set_decoder(decoder)

        received = []
        playback.frame_ready.connect(lambda f, tf: received.append((f, tf)))
        decoder.frame_ready.emit("new_decoder_frame")
        self.assertEqual(len(received), 1)

    def test_release_cleans_up(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.play()
        playback.release()

        self.assertFalse(playback.is_playing)
        self.assertIsNone(playback.decoder)

    def test_play_without_decoder_does_nothing(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        playback = TimelinePlayback(timeline)

        playback.play()
        self.assertFalse(playback.is_playing)

    def test_play_with_unloaded_decoder_does_nothing(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        decoder.is_loaded = False
        playback = TimelinePlayback(timeline, decoder)

        playback.play()
        self.assertFalse(playback.is_playing)

    def test_seek_without_decoder_still_updates_position(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        playback = TimelinePlayback(timeline)

        position = playback.seek(5)
        self.assertEqual(position.timeline_frame, 5)
        self.assertEqual(position.source_frame, 5)
        self.assertEqual(playback.current_timeline_frame, 5)

    def test_playback_position_dataclass(self):
        pos = PlaybackPosition(timeline_frame=10, source_frame=5, clip="test")
        self.assertEqual(pos.timeline_frame, 10)
        self.assertEqual(pos.source_frame, 5)
        self.assertEqual(pos.clip, "test")

    def test_playback_position_is_frozen(self):
        pos = PlaybackPosition(timeline_frame=1, source_frame=1, clip=None)
        with self.assertRaises(AttributeError):
            pos.timeline_frame = 2

    def test_get_fps_from_clips(self):
        timeline = Timeline()
        c = clip(0, 9, 0)
        c.fps = 24.0
        timeline.add_clip(c)
        playback = TimelinePlayback(timeline)

        self.assertEqual(playback._get_fps(), 24.0)

    def test_get_fps_default_when_no_clips(self):
        timeline = Timeline()
        playback = TimelinePlayback(timeline)

        self.assertEqual(playback._get_fps(), 30.0)

    # ------------------------------------------------------------------
    # Toggle / reverse
    # ------------------------------------------------------------------

    def test_toggle_playback_starts_and_stops(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.toggle_playback()
        self.assertTrue(playback.is_playing)

        playback.toggle_playback()
        self.assertFalse(playback.is_playing)

    def test_toggle_playback_resumes_from_current_position(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.seek(5)
        playback.toggle_playback()
        self.assertTrue(playback.is_playing)
        self.assertEqual(playback.current_timeline_frame, 5)

        playback.toggle_playback()
        self.assertFalse(playback.is_playing)
        self.assertEqual(playback.current_timeline_frame, 5)

    def test_play_reverse_sets_negative_direction(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.seek(5)
        playback.play_reverse()
        self.assertTrue(playback.is_playing)
        self.assertEqual(playback._play_direction, -1)

    def test_play_sets_forward_direction(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.play_reverse()
        playback.play()
        self.assertTrue(playback.is_playing)
        self.assertEqual(playback._play_direction, 1)

    def test_toggle_playback_without_decoder_does_nothing(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        playback = TimelinePlayback(timeline)

        playback.toggle_playback()
        self.assertFalse(playback.is_playing)

    def test_play_reverse_without_decoder_does_nothing(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        playback = TimelinePlayback(timeline)

        playback.play_reverse()
        self.assertFalse(playback.is_playing)

    # ------------------------------------------------------------------
    # Shuttle speed (JKL)
    # ------------------------------------------------------------------

    def test_initial_speed_is_1(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        playback = TimelinePlayback(timeline)

        self.assertEqual(playback.playback_speed, 1)

    def test_increase_forward_speed_cycles_1x_4x_8x(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.play()
        self.assertEqual(playback.playback_speed, 1)

        playback.increase_forward_speed()
        self.assertEqual(playback.playback_speed, 4)

        playback.increase_forward_speed()
        self.assertEqual(playback.playback_speed, 8)

        # Cycles back to 1x
        playback.increase_forward_speed()
        self.assertEqual(playback.playback_speed, 1)

    def test_increase_reverse_speed_cycles_neg1_neg4_neg8(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.play_reverse()
        self.assertEqual(playback.playback_speed, -1)

        playback.increase_reverse_speed()
        self.assertEqual(playback.playback_speed, -4)

        playback.increase_reverse_speed()
        self.assertEqual(playback.playback_speed, -8)

        # Cycles back to -1x
        playback.increase_reverse_speed()
        self.assertEqual(playback.playback_speed, -1)

    def test_k_resets_speed_to_1(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.play()
        playback.increase_forward_speed()
        playback.increase_forward_speed()
        self.assertEqual(playback.playback_speed, 8)

        playback.pause()
        playback.reset_playback_speed()
        self.assertEqual(playback.playback_speed, 1)

    def test_after_k_l_starts_at_1x_again(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.play()
        playback.increase_forward_speed()
        self.assertEqual(playback.playback_speed, 4)

        playback.pause()
        playback.reset_playback_speed()
        self.assertEqual(playback.playback_speed, 1)

        # L again starts at 1x
        playback.increase_forward_speed()
        self.assertEqual(playback.playback_speed, 1)

    def test_speed_property_positive_forward_negative_reverse(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.play()
        self.assertGreater(playback.playback_speed, 0)

        playback.play_reverse()
        self.assertLess(playback.playback_speed, 0)

    def test_increase_forward_speed_without_playing_sets_direction(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.increase_forward_speed()
        self.assertEqual(playback.playback_speed, 1)

        # play() uses current speed
        playback.play()
        self.assertEqual(playback.playback_speed, 1)

    def test_increase_reverse_speed_without_playing_sets_direction(self):
        timeline = Timeline()
        timeline.add_clip(clip(0, 9, 0))
        decoder = FakeDecoder()
        playback = TimelinePlayback(timeline, decoder)

        playback.increase_reverse_speed()
        self.assertEqual(playback.playback_speed, -1)

        playback.play_reverse()
        self.assertEqual(playback.playback_speed, -1)


if __name__ == "__main__":
    unittest.main()