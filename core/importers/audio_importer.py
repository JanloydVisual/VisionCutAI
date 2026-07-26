from uuid import uuid4

import subprocess
import json

from core.asset import Asset
from core.timeline.audio_clip import AudioClip


class AudioImporter:

    def __init__(self, project):

        self.project = project


    def get_audio_info(self, filepath):

        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=duration,sample_rate,channels",
            "-of",
            "json",
            filepath
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        data = json.loads(result.stdout)

        if not data.get("streams"):
            return None

        stream = data["streams"][0]

        return {
            "duration": float(
                stream.get("duration", 0)
            ),
            "sample_rate": int(
                stream.get("sample_rate", 48000)
            ),
            "channels": int(
                stream.get("channels", 2)
            )
        }


    def import_audio(self, filepath):

        info = self.get_audio_info(filepath)

        if info is None:
            return None


        asset = Asset(
            id=str(uuid4()),
            filepath=filepath,
            media_type="audio",
            duration=info["duration"]
        )


        self.project.assets.add(asset)


        clip = AudioClip(
            source_path=filepath,
            duration=info["duration"],
            sample_rate=info["sample_rate"],
            channels=info["channels"]
        )


        self.project.timeline.audio_tracks[0].add_clip(
            clip
        )


        return clip
