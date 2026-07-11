from core.importers.video_importer import VideoImporter


class ProjectImporter:

    def __init__(self, project):

        self.project = project

        self.video_importer = VideoImporter(
            project
        )


    def import_video(self, filepath):

        return self.video_importer.import_video(
            filepath
        )
