"""
FrameProcessor
--------------
Base interface for all frame processors used by ProcessingEngine.

Any future AI model (background removal, segmentation, matting,
etc.) plugs in by subclassing FrameProcessor and implementing
process(frame). ProcessingEngine, VideoPreview, and every other
part of the app remain completely unaware of what a given
processor actually does internally.
"""


class FrameProcessor:
    def process(self, frame):
        """Takes one raw frame, returns one processed frame."""
        raise NotImplementedError

    def set_quality(self, quality: str):
        """Adjusts the internal AI quality/resolution."""
        pass


class PassthroughProcessor(FrameProcessor):
    """
    Default processor for this milestone. Returns the frame
    completely unchanged - no AI model is wired in yet.
    """

    def process(self, frame):
        return frame
