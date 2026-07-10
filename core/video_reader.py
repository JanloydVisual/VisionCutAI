import cv2


class VideoReader:
    def __init__(self, video_path):

        self.video_path = video_path

        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {video_path}")

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_info(self):

        return {
            "Width": self.width,
            "Height": self.height,
            "FPS": self.fps,
            "Frames": self.frame_count,
        }

    def first_frame(self):

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        success, frame = self.cap.read()

        if not success:
            return None

        return frame

    def read(self):

        return self.cap.read()

    def release(self):

        self.cap.release()