from typing import Optional

from core.render.mask_cache_manager import MaskCacheManager, MaskCacheEntry

from core.ai.mask_refiner import MaskRefiner
from core.ai.alpha_refiner import AlphaRefiner
from core.render.preview_mode import PreviewMode

class MaskProvider:
    """
    Provides frame masks without exposing the generation source (cache vs TrackingEngine).
    Acts as the clean boundary between the Exporters and the AI tracking systems.
    """
    def __init__(self, mask_cache: MaskCacheManager, tracking_engine):
        self.mask_cache = mask_cache
        self.tracking_engine = tracking_engine
        self.mask_refiner = MaskRefiner()
        self.alpha_refiner = AlphaRefiner()
        
    def get_frame_mask(self, frame_index: int, allow_generate: bool = True, preview_mode: PreviewMode = PreviewMode.BALANCED) -> Optional[MaskCacheEntry]:
        # 1. Check MaskCacheManager
        cache_entry = self.mask_cache.get_mask(frame_index)
        
        # 2. If valid cached MaskCacheEntry exists
        if cache_entry is not None and cache_entry.validated:
            return cache_entry
            
        # 3. If missing and allow_generate=True
        if allow_generate and self.tracking_engine is not None:
            # 4. Generate and store (propagate_frame handles storing in cache)
            generated_entry = self.tracking_engine.propagate_frame(frame_index)
            
            if generated_entry is not None:
                # Refine mask edges
                generated_entry.mask = self.mask_refiner.refine(generated_entry.mask)
                
                # Sprint 34: Professional Alpha Matte Quality
                generated_entry.mask = self.alpha_refiner.refine(generated_entry.mask, mode=preview_mode)
                
                # Overwrite cache with refined mask
                self.mask_cache.store_mask(generated_entry)
                
            # 5. Return MaskCacheEntry
            return generated_entry
            
        return None
