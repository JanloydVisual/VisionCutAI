from .asset import Asset

class AssetManager:

    def __init__(self):

        self.assets = {}

    def add(self, asset: Asset):

        self.assets[asset.id] = asset

    def get(self, asset_id):

        return self.assets.get(asset_id)

    def remove(self, asset_id):

        self.assets.pop(asset_id, None)

    def clear(self):

        self.assets.clear()

    def all(self):

        return list(self.assets.values())
