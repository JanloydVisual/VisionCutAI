from PyQt6.QtCore import QThread

from core.project import Project
from core.video_engine import VideoEngine
from core.processing_engine import ProcessingEngine
from core.project_importer import ProjectImporter


class AppController:
    """
    Connects the GUI with the application engines.
    The GUI should never talk directly to VideoEngine or
    ProcessingEngine.
    """

    def __init__(self):
        self.project = Project()
        self.importer = ProjectImporter(self.project)

        self.video = VideoEngine()

        self.processing = ProcessingEngine()
        self._processing_thread = QThread()
        self.processing.moveToThread(self._processing_thread)
        self._processing_thread.start()

        self.video.frame_ready.connect(self.processing.enqueue_frame)

        self._init_ai_processor()

    def _init_ai_processor(self):
        """
        Attempts to replace the default PassthroughProcessor with
        BackgroundRemovalProcessor. If rembg/onnxruntime are not
        installed yet, silently keeps the passthrough so the app
        still launches normally via python app.py.
        """
        try:
            from ai.background_removal_processor import BackgroundRemovalProcessor
            processor = BackgroundRemovalProcessor()
            self.processing.set_processor(processor)
            self.ai_device_label = processor.device_label
        except Exception:
            self.ai_device_label = "AI unavailable (passthrough active)"

    # -------------------------
    # Video
    # -------------------------

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

        self._processing_thread.quit()
        self._processing_thread.wait()



