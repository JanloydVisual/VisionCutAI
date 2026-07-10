from uuid import uuid4

from core.video_reader import VideoReader
from core.asset import Asset
from core.clip import Clip


class ProjectImporter:

    def __init__(self, project):
        self.project = project

    def import_video(self, filepath):

        reader = VideoReader(filepath)
        info = reader.get_info()

        asset = Asset(
            id=str(uuid4()),
            filepath=filepath,
            media_type="video",
            width=info["Width"],
            height=info["Height"],
            fps=info["FPS"],
            frame_count=info["Frames"],
            duration=info["Frames"] / info["FPS"] if info["FPS"] > 0 else 0,
        )

        self.project.assets.add(asset)

        clip = Clip(
            source_path=filepath,
            start_frame=0,
            end_frame=info["Frames"] - 1,
            fps=info["FPS"],
            duration=asset.duration,
        )

        self.project.timeline.add_clip(clip)

        return info
