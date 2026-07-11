from core.project import Project
from core.video_engine import VideoEngine
from core.processing_engine import ProcessingEngine
from core.project_importer import ProjectImporter
from core.edit_history import EditHistory
from core.timeline_playback import TimelinePlayback


class AppController:
    """
    Connects the GUI with application engines without importing PyQt6.
    """

    def __init__(self):
        self.project = Project()
        self.importer = ProjectImporter(self.project)

        self.video = VideoEngine()

        self.processing = ProcessingEngine()
        self.processing.start()

        self._background_removal_processor = None
        self.background_removal_active = False
        self.background_removal_error = None
        self.frames_sent_to_processing = 0

        self.history = EditHistory()
        self._edit_snapshot = None

        # -- TimelinePlayback coordinator --------------------------------
        self.timeline_playback = TimelinePlayback(
            timeline=self.project.timeline,
            decoder=self.video,
        )

        # Expose the coordinator's frame-ready signal so MainWindow
        # gets (frame, timeline_frame) instead of just frame.
        self.frame_ready = self.timeline_playback.frame_ready

        # Keep the original VideoEngine.frame_ready connected for
        # the background-removal pipeline (unchanged path).
        self.video.frame_ready.connect(self._process_frame)

        self._init_ai_processor()

    def _init_ai_processor(self):
        try:
            from ai.background_removal_processor import BackgroundRemovalProcessor

            processor = BackgroundRemovalProcessor()
            self._background_removal_processor = processor
            self.ai_device_label = processor.device_label
        except Exception as error:
            self.background_removal_error = str(error)
            self.ai_device_label = "AI unavailable"

    @property
    def background_removal_available(self):
        return self._background_removal_processor is not None

    @property
    def background_removal_status(self):
        if self.background_removal_available:
            return f"Background removal ready ({self.ai_device_label})"
        return self.background_removal_error or "Background removal is unavailable"

    def start_background_removal(self):
        """Activates AI processing and processes the current preview frame."""
        if not self.video.is_loaded or not self.background_removal_available:
            return False

        self.processing.set_processor(self._background_removal_processor)
        self.background_removal_active = True

        # Re-emit the current frame for an immediate processed preview.
        # Seek the timeline to the current position, which maps to the
        # correct source frame via TimelinePlayback.
        self.timeline_playback.seek(self.timeline_playback.current_timeline_frame)
        return True

    def _process_frame(self, frame):
        """Sends playback frames to the AI pipeline after activation."""
        if self.background_removal_active:
            self.frames_sent_to_processing += 1
            self.processing.enqueue_frame(frame)

    def open_video(self, filepath):
        info = self.importer.import_video(filepath)
        success = self.video.load_video(filepath)
        if not success:
            return False

        # After loading, snap the timeline playhead to the first
        # playable frame (which maps to source frame 0).
        self.timeline_playback.seek(0)
        return info

    def toggle_playback(self):
        """Toggle between play and pause. Idempotent - safe to call repeatedly."""
        self.timeline_playback.toggle_playback()

    def play(self):
        self.timeline_playback.play()

    def play_reverse(self):
        """Start reverse playback (J key)."""
        self.timeline_playback.play_reverse()

    def pause(self):
        self.timeline_playback.pause()

    def stop(self):
        self.timeline_playback.stop()

    def next_frame(self):
        self.timeline_playback.step_forward()

    def previous_frame(self):
        self.timeline_playback.step_backward()

    def seek(self, frame_index):
        """Seek to *frame_index* in timeline-frame space."""
        self.timeline_playback.seek(frame_index)

    def selected_clip(self):
        return self.project.timeline.get_selected_clip()

    def select_clip(self, clip):
        return self.project.timeline.select_clip(clip)

    def begin_timeline_edit(self):
        if self._edit_snapshot is None:
            self._edit_snapshot = self.project.timeline.snapshot()

    def end_timeline_edit(self):
        if self._edit_snapshot is None:
            return False

        before = self._edit_snapshot
        self._edit_snapshot = None
        return self.history.record(before, self.project.timeline.snapshot())

    def _timeline_command(self, action):
        if self._edit_snapshot is not None:
            return action()
        return self.history.execute(self.project.timeline, action)

    def move_clip(self, clip, timeline_start_frame):
        return self._timeline_command(
            lambda: self.project.timeline.move_clip(clip, timeline_start_frame)
        )

    def trim_clip(self, clip, edge, timeline_frame):
        if edge == "start":
            return self._timeline_command(
                lambda: self.project.timeline.trim_clip_start(clip, timeline_frame)
            )
        if edge == "end":
            return self._timeline_command(
                lambda: self.project.timeline.trim_clip_end(clip, timeline_frame)
            )
        return False

    def split_selected_clip_at_playhead(self):
        clip = self.selected_clip()
        if clip is None:
            return False

        return self._timeline_command(
            lambda: self.project.timeline.split_clip(
                clip,
                self.timeline_playback.current_timeline_frame,
            )
        )

    def delete_selected_clip(self):
        return self._timeline_command(
            self.project.timeline.delete_selected_clip
        )

    def undo_timeline(self):
        return self.history.undo(self.project.timeline)

    def redo_timeline(self):
        return self.history.redo(self.project.timeline)

    def release(self):
        self.timeline_playback.release()
        self.video.release()
        self.processing.stop()