from dataclasses import dataclass, field
from typing import List

@dataclass
class MaskRange:
    """
    Defines a tracked sequence of frames for a specific object on the timeline.
    Supports multiple anchors and ranges for a single object.
    """
    object_id: str
    start_frame: int
    end_frame: int
    anchor_frames: List[int] = field(default_factory=list)
    
    def add_anchor(self, frame_index: int):
        if frame_index not in self.anchor_frames:
            self.anchor_frames.append(frame_index)
            self.anchor_frames.sort()
            
    def contains_frame(self, frame_index: int) -> bool:
        return self.start_frame <= frame_index <= self.end_frame
