from typing import List

from .clip import Clip
from .track import Track


class Timeline:
    """
    Owns all timeline edits. This central mutation point is the seam
    for a future undo/redo command history.
    """

    def __init__(self):
        self.tracks: List[Track] = [
            Track("Video Track 1", "video"),
            Track("Audio Track 1", "audio"),
        ]
        self.selected_clip: Clip | None = None

        # Multi-selection support for linked clips
        self.selected_clips = []

        self.revision = 0

    @property
    def clips(self):
        return self.video_tracks[0].clips

    @property
    def video_tracks(self):
        return [track for track in self.tracks if track.track_type == "video"]

    @property
    def audio_tracks(self):
        return [track for track in self.tracks if track.track_type == "audio"]

    def _track_for_clip(self, clip):
        for track in self.tracks:
            if clip in track.clips:
                return track
        return None

    @staticmethod
    def _sync_duration(clip):
        clip.duration = clip.frame_count / clip.fps if clip.fps > 0 else 0

    def get_linked_clips(self, target_clip: Clip) -> List[Clip]:
        """Return all clips that share a linked_id with the target_clip."""
        if getattr(target_clip, "linked_id", None) is None:
            return []
        
        linked = []
        for track in self.tracks:
            for clip in track.clips:
                if clip is not target_clip and getattr(clip, "linked_id", None) == getattr(target_clip, "linked_id", None):
                    linked.append(clip)
        return linked

    def _changed(self):
        # Future undo/redo can record snapshots/commands here.
        self.revision += 1

    def add_clip(self, clip: Clip):
        self.video_tracks[0].add_clip(clip)
        if self.selected_clip is None:
            self.selected_clip = clip
        self._changed()

    def add_audio_clip(self, audio_clip):
        self.audio_tracks[0].add_clip(audio_clip)
        self._changed()

    def remove_clip(self, clip: Clip):
        track = self._track_for_clip(clip)
        if track is None:
            return False

        track.remove_clip(clip)

        if self.selected_clip == clip:
            self.selected_clip = self.clips[0] if self.clips else None

        self._changed()
        return True

    def delete_selected_clip(self):
        if self.selected_clip is None:
            return False

        target = self.selected_clip
        clips_to_delete = [target] + self.get_linked_clips(target)

        # Keep a reference to the main track for selection later
        main_track = self._track_for_clip(target)

        for clip in clips_to_delete:
            track = self._track_for_clip(clip)
            if track:
                removed_start = clip.timeline_start_frame
                removed_duration = clip.frame_count
                track.remove_clip(clip)

                # Ripple delete: close the gap on this track
                for other_clip in track.clips:
                    if other_clip.timeline_start_frame > removed_start:
                        other_clip.timeline_start_frame -= removed_duration

        if main_track and main_track.clips:
            self.selected_clip = main_track.clips[0]
        else:
            self.selected_clip = self.clips[0] if self.clips else None

        self._changed()
        return True

    def select_clip(self, clip: Clip):
        if self._track_for_clip(clip) is None:
            return False
        self.selected_clip = clip
        return True

    def get_selected_clips(self):
        return self.selected_clips


    def clear_selection(self):
        self.selected_clips.clear()


    def add_to_selection(self, clip):
        if clip not in self.selected_clips:
            self.selected_clips.append(clip)

    def get_selected_clip(self):
        return self.selected_clip

    def clip_at_timeline_frame(self, timeline_frame: int):
        timeline_frame = int(timeline_frame)

        for clip in sorted(
            self.clips,
            key=lambda item: item.timeline_start_frame,
        ):
            if clip.timeline_start_frame <= timeline_frame <= clip.timeline_end_frame:
                return clip

        return None

    def next_playable_frame(self, timeline_frame: int):
        timeline_frame = int(timeline_frame)

        if self.clip_at_timeline_frame(timeline_frame) is not None:
            return timeline_frame

        for clip in sorted(
            self.clips,
            key=lambda item: item.timeline_start_frame,
        ):
            if clip.timeline_end_frame >= timeline_frame:
                return max(timeline_frame, clip.timeline_start_frame)

        return None

    def previous_playable_frame(self, timeline_frame: int):
        timeline_frame = int(timeline_frame)

        if self.clip_at_timeline_frame(timeline_frame) is not None:
            return timeline_frame

        for clip in sorted(
            self.clips,
            key=lambda item: item.timeline_start_frame,
            reverse=True,
        ):
            if clip.timeline_start_frame <= timeline_frame:
                return min(timeline_frame, clip.timeline_end_frame)

        return None

    def total_timeline_duration(self):
        if not self.clips:
            return 0

        return max(
            clip.timeline_end_frame
            for clip in self.clips
        ) + 1

    def move_clip(self, target_clip: Clip, timeline_start_frame: int):
        if self._track_for_clip(target_clip) is None:
            return False

        new_start = max(0, int(timeline_start_frame))
        delta = new_start - target_clip.timeline_start_frame
        
        if delta == 0:
            return True

        clips_to_move = [target_clip] + self.get_linked_clips(target_clip)
        
        # Safest min delta so nothing goes < 0
        min_current_start = min(clip.timeline_start_frame for clip in clips_to_move)
        if min_current_start + delta < 0:
            delta = -min_current_start

        for clip in clips_to_move:
            clip.timeline_start_frame += delta

        self.selected_clip = target_clip
        self._changed()
        return True

    def trim_clip_start(self, target_clip: Clip, timeline_frame: int):
        if self._track_for_clip(target_clip) is None:
            return False

        new_start = int(timeline_frame)
        if new_start <= target_clip.timeline_start_frame:
            return False
        if new_start > target_clip.timeline_end_frame:
            return False

        delta = new_start - target_clip.timeline_start_frame
        clips_to_trim = [target_clip] + self.get_linked_clips(target_clip)

        # Check if delta is valid for ALL linked clips
        for clip in clips_to_trim:
            expected_start = clip.timeline_start_frame + delta
            if expected_start <= clip.timeline_start_frame or expected_start > clip.timeline_end_frame:
                return False

        for clip in clips_to_trim:
            if hasattr(clip, 'start_frame'):
                clip.start_frame += delta
                clip.timeline_start_frame += delta
                self._sync_duration(clip)
            else:
                # AudioClip
                clip.duration -= delta / clip.fps
                clip.timeline_start_frame += delta

        self.selected_clip = target_clip
        self._changed()
        return True

    def trim_clip_end(self, target_clip: Clip, timeline_frame: int):
        if self._track_for_clip(target_clip) is None:
            return False

        new_end = int(timeline_frame)
        if new_end < target_clip.timeline_start_frame:
            return False
        if new_end >= target_clip.timeline_end_frame:
            return False

        delta = new_end - target_clip.timeline_end_frame
        clips_to_trim = [target_clip] + self.get_linked_clips(target_clip)

        for clip in clips_to_trim:
            expected_end = clip.timeline_end_frame + delta
            if expected_end < clip.timeline_start_frame or expected_end >= clip.timeline_end_frame:
                return False

        for clip in clips_to_trim:
            if hasattr(clip, 'end_frame'):
                kept_frames = clip.timeline_end_frame + delta - clip.timeline_start_frame + 1
                clip.end_frame = clip.start_frame + kept_frames - 1
                self._sync_duration(clip)
            else:
                # AudioClip
                clip.duration += delta / clip.fps

        self.selected_clip = target_clip
        self._changed()
        return True

    def split_clip(self, target_clip: Clip, timeline_frame: int):
        split_frame = int(timeline_frame)
        clips_to_split = [target_clip] + self.get_linked_clips(target_clip)
        
        import uuid
        # If the original clip is linked, generate a new linked_id for the right halves
        new_linked_id = str(uuid.uuid4()) if getattr(target_clip, "linked_id", None) else None
        
        success = False
        last_right_clip = None
        
        for clip in clips_to_split:
            track = self._track_for_clip(clip)
            if track is None:
                continue

            # Check if this clip spans the split point
            if split_frame <= clip.timeline_start_frame or split_frame > clip.timeline_end_frame:
                continue

            offset = split_frame - clip.timeline_start_frame
            
            if hasattr(clip, 'start_frame'):
                original_end_frame = clip.end_frame
                right_clip = type(clip)(
                    source_path=clip.source_path,
                    start_frame=clip.start_frame + offset,
                    end_frame=original_end_frame,
                    fps=clip.fps,
                    duration=0,
                    timeline_start_frame=split_frame,
                    background_removed=getattr(clip, 'background_removed', False),
                    effects=list(getattr(clip, 'effects', [])),
                )
                clip.end_frame = right_clip.start_frame - 1
                self._sync_duration(clip)
                self._sync_duration(right_clip)
            else:
                # AudioClip
                original_duration = clip.duration
                left_duration = offset / clip.fps
                right_duration = original_duration - left_duration
                
                right_clip = type(clip)(
                    source_path=clip.source_path,
                    duration=right_duration,
                    fps=clip.fps,
                    timeline_start_frame=split_frame,
                )
                # copy specific audio properties if they exist
                for attr in ['sample_rate', 'channels', 'muted']:
                    if hasattr(clip, attr):
                        setattr(right_clip, attr, getattr(clip, attr))
                
                clip.duration = left_duration
            
            if new_linked_id:
                right_clip.linked_id = new_linked_id

            insert_index = track.clips.index(clip) + 1
            track.clips.insert(insert_index, right_clip)
            
            if clip == target_clip:
                last_right_clip = right_clip
            success = True

        if success and last_right_clip:
            self.selected_clip = last_right_clip
            self._changed()
            
        return success

    def toggle_link_selected_clip(self):
        if self.selected_clip is None:
            return False
            
        target = self.selected_clip
        if getattr(target, 'linked_id', None) is not None:
            # Unlink
            linked_clips = self.get_linked_clips(target)
            target.linked_id = None
            for clip in linked_clips:
                clip.linked_id = None
            self._changed()
            return True
        else:
            # Try to Link
            import uuid
            new_id = str(uuid.uuid4())
            target.linked_id = new_id
            
            candidate_found = False
            for track in self.tracks:
                if track == self._track_for_clip(target):
                    continue
                for clip in track.clips:
                    if (clip.source_path == target.source_path and 
                        getattr(clip, 'linked_id', None) is None and
                        clip.timeline_start_frame == target.timeline_start_frame):
                        clip.linked_id = new_id
                        candidate_found = True
                        break
                if candidate_found:
                    break
                    
            if not candidate_found:
                target.linked_id = None
                return False
                
            self._changed()
            return True

    def snapshot(self):
        tracks_data = []
        selected_track_index = None
        selected_clip_index = None

        for t_idx, track in enumerate(self.tracks):
            clips_data = []
            for c_idx, clip in enumerate(track.clips):
                if clip == self.selected_clip:
                    selected_track_index = t_idx
                    selected_clip_index = c_idx

                if hasattr(clip, 'start_frame'):
                    # Video Clip
                    clips_data.append({
                        "type": "video",
                        "source_path": clip.source_path,
                        "start_frame": clip.start_frame,
                        "end_frame": clip.end_frame,
                        "fps": clip.fps,
                        "duration": clip.duration,
                        "timeline_start_frame": clip.timeline_start_frame,
                        "background_removed": getattr(clip, 'background_removed', False),
                        "effects": list(getattr(clip, 'effects', [])),
                        "linked_id": getattr(clip, 'linked_id', None),
                    })
                else:
                    # AudioClip
                    clips_data.append({
                        "type": "audio",
                        "source_path": clip.source_path,
                        "duration": clip.duration,
                        "fps": clip.fps,
                        "sample_rate": getattr(clip, 'sample_rate', 48000),
                        "channels": getattr(clip, 'channels', 2),
                        "timeline_start_frame": clip.timeline_start_frame,
                        "muted": getattr(clip, 'muted', False),
                        "linked_id": getattr(clip, 'linked_id', None),
                    })

            tracks_data.append({
                "name": track.name,
                "track_type": track.track_type,
                "clips": clips_data,
            })

        return {
            "tracks": tracks_data,
            "selected_track_index": selected_track_index,
            "selected_clip_index": selected_clip_index,
        }

    def restore(self, snapshot):
        from core.clip import Clip
        from core.audio_clip import AudioClip
        from core.track import Track

        self.tracks.clear()

        for track_data in snapshot.get("tracks", []):
            track = Track(track_data["name"], track_data["track_type"])
            for clip_data in track_data["clips"]:
                if clip_data.get("type", "video") == "video":
                    clip = Clip(
                        source_path=clip_data["source_path"],
                        start_frame=clip_data["start_frame"],
                        end_frame=clip_data["end_frame"],
                        fps=clip_data["fps"],
                        duration=clip_data["duration"],
                        timeline_start_frame=clip_data["timeline_start_frame"],
                        background_removed=clip_data.get("background_removed", False),
                        effects=list(clip_data.get("effects", [])),
                    )
                    clip.linked_id = clip_data.get("linked_id", None)
                    track.add_clip(clip)
                else:
                    clip = AudioClip(
                        source_path=clip_data["source_path"],
                        duration=clip_data["duration"],
                        fps=clip_data["fps"],
                        sample_rate=clip_data.get("sample_rate", 48000),
                        channels=clip_data.get("channels", 2),
                        timeline_start_frame=clip_data["timeline_start_frame"],
                        muted=clip_data.get("muted", False),
                    )
                    clip.linked_id = clip_data.get("linked_id", None)
                    track.add_clip(clip)
            self.tracks.append(track)

        t_idx = snapshot.get("selected_track_index")
        c_idx = snapshot.get("selected_clip_index")

        if t_idx is not None and c_idx is not None and t_idx < len(self.tracks):
            track = self.tracks[t_idx]
            if c_idx < len(track.clips):
                self.selected_clip = track.clips[c_idx]
            else:
                self.selected_clip = None
        else:
            self.selected_clip = None

        self._changed()

    def clear(self):
        for track in self.tracks:
            track.clips.clear()
        self.selected_clip = None
        self._changed()

    def __len__(self):
        return len(self.clips)

    def __iter__(self):
        return iter(self.clips)
