class Playhead:
    def __init__(self, fps: float = 30.0):
        if fps <= 0:
            raise ValueError("fps must be greater than zero")
        self.fps = fps
        self.current_frame = 0
        self.is_playing = False

    def seek(self, frame: int):
        if frame < 0:
            frame = 0
        self.current_frame = frame

    def advance(self, frames: int):
        new_frame = self.current_frame + frames
        if new_frame < 0:
            new_frame = 0
        self.current_frame = new_frame

    def get_time(self) -> float:
        return self.current_frame / self.fps
