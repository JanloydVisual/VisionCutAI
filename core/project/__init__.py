from ..timeline.timeline import Timeline
from ..asset_manager import AssetManager

class Project:

    def __init__(self):

        self.name = "Untitled Project"

        self.modified = False

        self.assets = AssetManager()

        self.timeline = Timeline()

    def new(self):

        self.assets.clear()

        self.timeline.clear()

        self.modified = False
