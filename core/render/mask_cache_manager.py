import threading
import time
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import numpy as np

from core.ai.anchor_manager import QualityGrade


@dataclass
class MaskCacheEntry:
    frame_index: int
    mask: np.ndarray
    bbox: Tuple[int, int, int, int]
    quality_grade: QualityGrade
    confidence: float
    anchor_source: str
    timestamp: float
    validated: bool


class MaskCacheManager:
    """
    Shared infrastructure for storing and retrieving generated alpha masks.
    Used by Viewer Preview, TrackingEngine, and Exporters.
    Thread-safe.
    """
    
    def __init__(self):
        self._cache: Dict[int, MaskCacheEntry] = {}
        self._lock = threading.RLock()
        
        # Telemetry
        self.cache_hits = 0
        self.cache_misses = 0
        self.generated_masks = 0
        self.invalidated_masks = 0
        
    def store_mask(self, entry: MaskCacheEntry):
        with self._lock:
            self._cache[entry.frame_index] = entry
            self.generated_masks += 1
            
    def get_mask(self, frame_index: int) -> Optional[MaskCacheEntry]:
        with self._lock:
            if frame_index in self._cache:
                self.cache_hits += 1
                return self._cache[frame_index]
            self.cache_misses += 1
            return None
            
    def has_mask(self, frame_index: int) -> bool:
        with self._lock:
            return frame_index in self._cache
            
    def invalidate_range(self, start: int, end: int):
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if start <= k <= end]
            for k in keys_to_remove:
                del self._cache[k]
            self.invalidated_masks += len(keys_to_remove)
                
    def invalidate_from(self, frame_index: int):
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if k >= frame_index]
            for k in keys_to_remove:
                del self._cache[k]
            self.invalidated_masks += len(keys_to_remove)
                
    def clear(self):
        with self._lock:
            self.invalidated_masks += len(self._cache)
            self._cache.clear()
