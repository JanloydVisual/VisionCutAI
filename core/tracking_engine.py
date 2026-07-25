import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Dict, List, Optional, Tuple
from core.ai.object_tracker import TrackedFrameState

class TrackingEngine(QThread):
    progress_updated = pyqtSignal(int, int, float) # current_frame, total_frames, confidence
    tracking_completed = pyqtSignal()
    tracking_failed = pyqtSignal(str)
    tracking_paused = pyqtSignal(str)

    def __init__(self, video_engine, object_tracker):
        super().__init__()
        self.video_engine = video_engine
        self.object_tracker = object_tracker
        self._is_running = False
        
        self.start_frame = 0
        self.end_frame = 0
        
        # Cache mapping source_frame_index -> TrackedFrameState
        self.tracking_cache: Dict[int, TrackedFrameState] = {}
        
        self.confidence_threshold = 0.6

    def start_tracking(self, start_frame: int, end_frame: int):
        self.start_frame = start_frame
        self.end_frame = end_frame
        
        # Keep the initial frame's tracking state since it's already initialized
        initial_state = self.object_tracker.get_state()
        if initial_state:
            self.tracking_cache[start_frame] = initial_state
            
        self._is_running = True
        self.start()

    def run(self):
        try:
            total_frames = self.end_frame - self.start_frame
            
            # Start tracking from the NEXT frame
            for i in range(self.start_frame + 1, self.end_frame + 1):
                if not self._is_running:
                    break
                    
                frame = self.video_engine.get_frame(i)
                if frame is None:
                    continue
                    
                if frame.shape[2] == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    
                state = self.object_tracker.update(frame, frame_number=i)
                if state is not None:
                    if state.confidence < self.confidence_threshold:
                        self.tracking_paused.emit(f"Tracking lost at frame {i}. Confidence too low ({state.confidence:.2f}).")
                        break
                    
                    self.tracking_cache[i] = state
                else:
                    self.tracking_paused.emit(f"Tracking completely lost at frame {i}.")
                    break
                    
                # Emit progress every 3 frames to avoid UI spam but keep it smooth
                if (i - self.start_frame) % 3 == 0:
                    self.progress_updated.emit(i - self.start_frame, total_frames, state.confidence)

            if self._is_running:
                # Only emit completed if we didn't pause/fail early
                self.progress_updated.emit(total_frames, total_frames, 1.0)
                self.tracking_completed.emit()
            
        except Exception as e:
            self.tracking_failed.emit(str(e))
        finally:
            self._is_running = False

    def stop(self):
        self._is_running = False
        self.wait()
        
    def get_tracked_prompt(self, frame_index: int, label: int = 1) -> Optional[list]:
        state = self.tracking_cache.get(frame_index)
        if state:
            return self.object_tracker.get_sam_prompt(state)
        return None
