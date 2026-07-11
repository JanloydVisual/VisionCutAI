from core.project import Project
from core.video_engine import VideoEngine
from core.processing_engine import ProcessingEngine
from core.project_importer import ProjectImporter


class AppController:
    """
    Connects the GUI with the application engines. Contains no
    PyQt6 imports - this class is now portable Core layer code,
    reusable by any future frontend.
    """

    def __init__(self):
        self.project = Project()
        self.importer = ProjectImporter(self.project)

        self.video = VideoEngine()

        self.processing = ProcessingEngine()
        self.processing.start()

        self.video.frame_ready.connect(self.processing.enqueue_frame)

        self._init_ai_processor()

    def _init_ai_processor(self):
        try:
            from ai.background_removal_processor import BackgroundRemovalProcessor
            processor = BackgroundRemovalProcessor()
            self.processing.set_processor(processor)
            self.ai_device_label = processor.device_label
        except Exception:
            self.ai_device_label = "AI unavailable (passthrough active)"

    def open_video(self, filepath):
        info = self.importer.import_video(filepath)
        success = self.video.load_video(filepath)
        if not success:
            return False
        return info

    def play(self):
        self.video.play()

    def pause(self):
        self.video.pause()

    def stop(self):
        self.video.stop()

    def next_frame(self):
        self.video.next_frame()

    def previous_frame(self):
        self.video.previous_frame()

    def seek(self, frame_index):
        self.video.seek(frame_index)

    def selected_clip(self):
        return self.project.timeline.get_selected_clip()

    def release(self):
        self.video.release()
        self.processing.stop()
