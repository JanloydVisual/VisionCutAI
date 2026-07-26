import os
from typing import Dict, Any

class ResolveBridge:
    """
    DaVinci Resolve Workflow Bridge:
    Handles generation of Resolve-friendly export presets, folder organization, and validation.
    """
    def __init__(self, export_dir: str):
        self.export_dir = export_dir

    def create_project_structure(self):
        """Creates the folder structure required for a clean Resolve import."""
        directories = ["originals", "masks", "alpha_exports", "metadata"]
        for d in directories:
            path = os.path.join(self.export_dir, d)
            os.makedirs(path, exist_ok=True)
            
    def get_resolve_preset(self, format_type: str) -> Dict[str, Any]:
        """Returns the optimal settings for Resolve ingestion."""
        if format_type == "png_sequence":
            return {
                "format": "PNG",
                "alpha_channel": True,
                "color_space": "RGBA",
                "naming_convention": "frame_%06d.png"
            }
        elif format_type == "prores_4444":
            return {
                "format": "QuickTime",
                "codec": "ProRes_4444",
                "alpha_channel": True
            }
        return {}

    def validate_export(self, expected_frames: int, exported_frames: int, alpha_missing: bool, tracking_warnings: list) -> Dict[str, Any]:
        """Validates the export to ensure Resolve won't complain about broken sequences."""
        status = "PASSED"
        reasons = []
        
        if expected_frames != exported_frames:
            status = "FAILED"
            reasons.append(f"Frame count mismatch: expected {expected_frames}, got {exported_frames}")
            
        if alpha_missing:
            status = "FAILED"
            reasons.append("Missing alpha channel in sequence")
            
        if len(tracking_warnings) > 0:
            if status != "FAILED":
                status = "WARNING"
            reasons.append(f"Tracking warnings present: {len(tracking_warnings)}")
            
        return {
            "status": status,
            "reasons": reasons
        }
