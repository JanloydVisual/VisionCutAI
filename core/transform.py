from dataclasses import dataclass


@dataclass
class Transform:

    position_x: float = 0.0
    position_y: float = 0.0

    scale_x: float = 1.0
    scale_y: float = 1.0

    rotation: float = 0.0

    opacity: float = 1.0

    anchor_x: float = 0.5
    anchor_y: float = 0.5
