import threading
import time
from typing import Optional
import queue

from core.render.mask_provider import MaskProvider

class MaskPrefetcher:
    """
    Background worker that fetches masks ahead of the playhead.
    Observes timeline frame and playback direction, requests masks through MaskProvider.
    Uses standard threading to remain UI independent.
    """
    def __init__(self, mask_provider: MaskProvider):
        self.mask_provider = mask_provider
        self.current_frame = 0
        self.direction = 1
        self.lookahead = 10
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
    def set_playback_state(self, current_frame: int, direction: int, lookahead: int = 10):
        with self._lock:
            self.current_frame = current_frame
            self.direction = direction
            self.lookahead = lookahead

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            
        self._thread = threading.Thread(target=self._prefetch_loop, daemon=True, name="MaskPrefetcher")
        self._thread.start()
        
    def stop(self):
        with self._lock:
            self._running = False
            
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None
            
    def _prefetch_loop(self):
        while True:
            with self._lock:
                if not self._running:
                    break
                curr = self.current_frame
                dir = self.direction
                lookahead = self.lookahead
                
            # Try to prefetch frames ahead
            prefetched_any = False
            for offset in range(1, lookahead + 1):
                target_frame = curr + (offset * dir)
                if target_frame < 0:
                    continue
                    
                # Check if it's already in memory cache
                # We call get_frame_mask which will generate if not found
                if not self.mask_provider.mask_cache.has_mask(target_frame):
                    # Request generation
                    self.mask_provider.get_frame_mask(target_frame, allow_generate=True)
                    prefetched_any = True
                    break # Only do one expensive generation per loop iteration
                    
            if not prefetched_any:
                time.sleep(0.05) # Idle if everything is cached
