import os
import json
import cv2
import numpy as np
from typing import Dict, Optional, Any
from pathlib import Path

from core.render.mask_cache_manager import MaskCacheEntry
from core.ai.anchor_manager import QualityGrade

class ProjectCache:
    """
    Persistent storage layer for masks.
    Does not contain AI or tracking logic.
    """
    def __init__(self, cache_dir: str = "project_cache"):
        self.cache_dir = Path(cache_dir)
        self.masks_dir = self.cache_dir / "masks"
        self.metadata_path = self.cache_dir / "metadata.json"
        
        self.masks_dir.mkdir(parents=True, exist_ok=True)
        
    def save_cache(self, entries: Dict[int, MaskCacheEntry], video_hash: str):
        metadata = {
            "cache_version": 1,
            "video_hash": video_hash,
            "frames": {}
        }
        
        for frame_index, entry in entries.items():
            if not entry.validated:
                continue
                
            frame_meta = {
                "frame_index": entry.frame_index,
                "quality_grade": entry.quality_grade.name,
                "confidence": float(entry.confidence),
                "bbox": entry.bbox,
                "anchor_source": entry.anchor_source,
                "timestamp": entry.timestamp,
                "validated": entry.validated
            }
            metadata["frames"][str(frame_index)] = frame_meta
            
            mask_path = self.masks_dir / f"frame_{frame_index:06d}.png"
            # Masks are stored as grayscale PNG alpha images
            cv2.imwrite(str(mask_path), entry.mask)
            
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
    def load_cache(self, current_video_hash: str) -> Dict[int, MaskCacheEntry]:
        if not self.metadata_path.exists():
            return {}
            
        with open(self.metadata_path, 'r') as f:
            try:
                metadata = json.load(f)
            except json.JSONDecodeError:
                return {}
                
        if metadata.get("video_hash") != current_video_hash:
            # Video hash mismatch, invalidate cache
            self.clear_cache()
            return {}
            
        entries = {}
        frames_meta = metadata.get("frames", {})
        
        for str_idx, frame_meta in frames_meta.items():
            frame_index = int(str_idx)
            mask_path = self.masks_dir / f"frame_{frame_index:06d}.png"
            
            if not mask_path.exists():
                continue
                
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                continue
                
            quality_grade_name = frame_meta.get("quality_grade", "GOOD")
            try:
                quality_grade = QualityGrade[quality_grade_name]
            except KeyError:
                quality_grade = QualityGrade.GOOD
                
            entry = MaskCacheEntry(
                frame_index=frame_meta.get("frame_index", frame_index),
                mask=mask,
                bbox=tuple(frame_meta.get("bbox", (0,0,0,0))),
                quality_grade=quality_grade,
                confidence=frame_meta.get("confidence", 1.0),
                anchor_source=frame_meta.get("anchor_source", "Unknown"),
                timestamp=frame_meta.get("timestamp", 0.0),
                validated=frame_meta.get("validated", True)
            )
            entries[frame_index] = entry
            
        return entries
        
    def clear_cache(self):
        if self.masks_dir.exists():
            for f in self.masks_dir.glob("*.png"):
                f.unlink()
        if self.metadata_path.exists():
            self.metadata_path.unlink()
