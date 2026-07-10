from core.video_engine import VideoEngine


class AppController:
    """
    Connects the GUI with the application engines.
    The GUI should never talk directly to VideoEngine.
    """

    def __init__(self):
        self.video = VideoEngine()

    # -------------------------
    # Video
    # -------------------------

    def open_video(self, filepath):
        return self.video.load_video(filepath)

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

    def release(self):
        self.video.release()
