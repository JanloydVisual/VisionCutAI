import json
import os
from enum import Enum, auto
from typing import Dict, Any, Optional

class PresetManager:
    """
    Manages saving and loading of compositing, preview, and object settings.
    """
    def __init__(self, storage_path="presets.json"):
        self.storage_path = storage_path
        self.presets: Dict[str, Dict[str, Any]] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            except Exception:
                self.presets = {}
        else:
            self.presets = {
                "Default": {
                    "compositing": {"bg_mode": "Original", "blur": 21, "opacity": 100, "feather": 3},
                    "preview": {"quality": "Balanced"},
                    "object": {"mode": "auto"}
                }
            }

    def _save_to_disk(self):
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.presets, f, indent=4)

    def save_preset(self, name: str, compositing: dict, preview: dict, object_settings: dict):
        self.presets[name] = {
            "compositing": compositing,
            "preview": preview,
            "object": object_settings
        }
        self._save_to_disk()

    def load_preset(self, name: str) -> Optional[Dict[str, Any]]:
        return self.presets.get(name)

    def delete_preset(self, name: str):
        if name in self.presets and name != "Default":
            del self.presets[name]
            self._save_to_disk()
            
    def get_preset_names(self) -> list:
        return list(self.presets.keys())
