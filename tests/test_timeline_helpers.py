from core.clip import Clip
from core.timeline import Timeline


def make_clip(source_start, source_end, timeline_start):
    return Clip(
        source_path="video.mp4",
        start_frame=source_start,
        end_frame=source_end,
        fps=30.0,
        duration=(source_end - source_start + 1) / 30.0,
        timeline_start_frame=timeline_start,
    )


def edited_timeline():
    timeline = Timeline()
    first = make_clip(0, 4, 0)       # Timeline frames 0?4
    second = make_clip(5, 9, 8)      # Timeline frames 8?12; gap 5?7
    timeline.add_clip(first)
    timeline.add_clip(second)
    return timeline, first, second


def test_clip_at_timeline_frame_returns_matching_clip():
    timeline, first, second = edited_timeline()

    assert timeline.clip_at_timeline_frame(0) is first
    assert timeline.clip_at_timeline_frame(4) is first
    assert timeline.clip_at_timeline_frame(8) is second
    assert timeline.clip_at_timeline_frame(12) is second


def test_clip_at_timeline_frame_returns_none_in_gaps():
    timeline, _, _ = edited_timeline()

    assert timeline.clip_at_timeline_frame(5) is None
    assert timeline.clip_at_timeline_frame(7) is None
    assert timeline.clip_at_timeline_frame(13) is None


def test_next_playable_frame_moves_inside_or_jumps_over_gap():
    timeline, _, _ = edited_timeline()

    assert timeline.next_playable_frame(2) == 2
    assert timeline.next_playable_frame(5) == 8
    assert timeline.next_playable_frame(7) == 8
    assert timeline.next_playable_frame(13) is None


def test_previous_playable_frame_moves_inside_or_jumps_over_gap():
    timeline, _, _ = edited_timeline()

    assert timeline.previous_playable_frame(10) == 10
    assert timeline.previous_playable_frame(7) == 4
    assert timeline.previous_playable_frame(5) == 4
    assert timeline.previous_playable_frame(-1) is None


def test_total_timeline_duration_uses_last_edited_clip_frame():
    timeline, _, _ = edited_timeline()

    assert timeline.total_timeline_duration() == 13
