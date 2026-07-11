"""
Background-removal processor using rembg and ONNX Runtime.
"""

import numpy as np

from core.frame_processor import FrameProcessor


class BackgroundRemovalInitializationError(RuntimeError):
    """Explains why the optional background-removal feature is unavailable."""


class BackgroundRemovalProcessor(FrameProcessor):

    def __init__(self, model_name: str = "u2net"):
        try:
            from rembg import new_session
        except ImportError as error:
            raise BackgroundRemovalInitializationError(
                "Background removal requires rembg. Run: "
                "python -m pip install rembg onnxruntime"
            ) from error

        providers = self._resolve_providers()
        self.device_label = "GPU" if "CUDAExecutionProvider" in providers else "CPU"

        try:
            # On first use, rembg downloads and caches the selected model.
            self._session = new_session(model_name, providers=providers)
        except Exception as error:
            raise BackgroundRemovalInitializationError(
                f"Could not load the {model_name} background-removal model. "
                "Check your internet connection for the first download, then "
                f"restart the app. Details: {error}"
            ) from error

    @staticmethod
    def _resolve_providers():
        try:
            import onnxruntime as ort
        except ImportError as error:
            raise BackgroundRemovalInitializationError(
                "Background removal requires ONNX Runtime. Run: "
                "python -m pip install onnxruntime"
            ) from error

        available = ort.get_available_providers()

        if "CPUExecutionProvider" not in available:
            raise BackgroundRemovalInitializationError(
                "ONNX Runtime has no usable CPU provider. Reinstall it with: "
                "python -m pip install --upgrade onnxruntime"
            )

        if "CUDAExecutionProvider" in available:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]

        return ["CPUExecutionProvider"]

    def process(self, frame):
        """
        frame: BGR numpy array from VideoEngine.
        returns: RGBA numpy array for the processed preview.
        """
        from rembg import remove

        try:
            rgb_frame = frame[:, :, ::-1]
            return remove(rgb_frame, session=self._session)
        except Exception:
            # Preserve video playback if one frame fails to process.
            h, w = frame.shape[:2]
            rgb_frame = frame[:, :, ::-1]
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
            return np.concatenate([rgb_frame, alpha], axis=2)
