"""
BackgroundRemovalProcessor
---------------------------
FrameProcessor implementation using rembg (ONNX-based background
removal). Chosen over BiRefNet for this integration: rembg wraps
proven segmentation models (u2net, isnet-general-use, etc.) behind
a trivial API, auto-downloads/caches weights, and natively supports
CUDA with automatic CPU fallback via onnxruntime providers - all of
which BiRefNet requires substantial manual work for for a real-time
video preview use case.

Implements the existing FrameProcessor interface only. Has no
knowledge of ProcessingEngine, VideoEngine, or any UI component.
"""

import numpy as np

from core.frame_processor import FrameProcessor


class BackgroundRemovalProcessor(FrameProcessor):

    def __init__(self, model_name: str = "u2net"):
        from rembg import new_session

        providers = self._resolve_providers()
        self.device_label = "GPU" if "CUDAExecutionProvider" in providers else "CPU"

        self._session = new_session(model_name, providers=providers)

    @staticmethod
    def _resolve_providers():
        try:
            import onnxruntime as ort
            available = ort.get_available_providers()
        except Exception:
            available = []

        if "CUDAExecutionProvider" in available:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]

        return ["CPUExecutionProvider"]

    def process(self, frame):
        """
        frame: BGR numpy array (H, W, 3), as emitted by VideoEngine.
        Returns: RGBA numpy array (H, W, 4).
        """
        from rembg import remove

        try:
            rgb_frame = frame[:, :, ::-1]  # BGR -> RGB, no copy
            rgba = remove(rgb_frame, session=self._session)
            return rgba
        except Exception:
            # A failed inference must never break playback or the
            # processing thread - fall back to an opaque RGBA
            # version of the original frame.
            h, w = frame.shape[:2]
            rgb_frame = frame[:, :, ::-1]
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
            return np.concatenate([rgb_frame, alpha], axis=2)
