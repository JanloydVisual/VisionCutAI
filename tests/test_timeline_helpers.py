from core.timeline.clip import Clip
from core.timeline.timeline import Timeline


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

def test_linked_clip_move():
    timeline = Timeline()
    video = make_clip(0, 10, 0)
    audio = make_clip(0, 10, 0)
    from core.link_manager import LinkManager
    LinkManager.link(video, audio)
    timeline.add_clip(video)
    timeline.add_audio_clip(audio)

    timeline.move_clip(video, 5)

    assert video.timeline_start_frame == 5
    assert audio.timeline_start_frame == 5

def test_linked_clip_split():
    timeline = Timeline()
    video = make_clip(0, 10, 0)
    audio = make_clip(0, 10, 0)
    from core.link_manager import LinkManager
    LinkManager.link(video, audio)
    timeline.add_clip(video)
    timeline.add_audio_clip(audio)

    timeline.split_clip(video, 5)

    assert len(timeline.video_tracks[0].clips) == 2
    assert len(timeline.audio_tracks[0].clips) == 2

    left_video = timeline.video_tracks[0].clips[0]
    right_video = timeline.video_tracks[0].clips[1]
    left_audio = timeline.audio_tracks[0].clips[0]
    right_audio = timeline.audio_tracks[0].clips[1]

    assert left_video.timeline_end_frame == 4
    assert left_audio.timeline_end_frame == 4
    assert right_video.timeline_start_frame == 5
    assert right_audio.timeline_start_frame == 5

    # Check they share the original linked_id
    assert left_video.linked_id == left_audio.linked_id
    # Check the right halves got a newly generated matching linked_id
    assert right_video.linked_id == right_audio.linked_id
    assert right_video.linked_id != left_video.linked_id

def test_linked_clip_delete():
    timeline = Timeline()
    video1 = make_clip(0, 10, 0)
    audio1 = make_clip(0, 10, 0)
    video2 = make_clip(11, 20, 11)
    audio2 = make_clip(11, 20, 11)
    from core.link_manager import LinkManager
    LinkManager.link(video1, audio1)
    LinkManager.link(video2, audio2)

    timeline.add_clip(video1)
    timeline.add_clip(video2)
    timeline.add_audio_clip(audio1)
    timeline.add_audio_clip(audio2)

    timeline.select_clip(video1)
    timeline.delete_selected_clip()

    # Video1 and Audio1 should be deleted.
    assert len(timeline.video_tracks[0].clips) == 1
    assert len(timeline.audio_tracks[0].clips) == 1

    # Video2 and Audio2 should ripple backwards by video1's frame_count (11 frames)
    assert timeline.video_tracks[0].clips[0].timeline_start_frame == 0
    assert timeline.audio_tracks[0].clips[0].timeline_start_frame == 0
