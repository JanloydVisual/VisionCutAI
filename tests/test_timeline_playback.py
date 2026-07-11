import unittest

from core.clip import Clip
from core.edit_history import EditHistory
from core.timeline import Timeline
from core.timeline_playback import TimelinePlayback


class FakeDecoder:
    def __init__(self):
        self.seek_calls = []
        self.current_frame = None

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


if __name__ == "__main__":
    unittest.main()
