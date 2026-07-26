from enum import Enum, auto

class PreviewMode(Enum):
    """
    Defines the visual quality and computational cost of mask rendering during timeline playback.
    """
    FAST = auto()
    BALANCED = auto()
    FINE_DETAIL = auto()
    MAXIMUM_QUALITY = auto()

