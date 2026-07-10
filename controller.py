from video_reader import VideoReader


class AppController:
    def __init__(self):
        self.video = None

    def open_video(self, filename):
        self.video = VideoReader(filename)
        return self.video.get_info()

    def first_frame(self):
        if self.video is None:
            return None

        return self.video.first_frame()

    def close_video(self):
        if self.video:
            self.video.release()