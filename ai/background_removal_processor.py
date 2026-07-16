"""
Background-removal processor using rembg and ONNX Runtime.
"""

import numpy as np

from core.frame_processor import FrameProcessor


class BackgroundRemovalInitializationError(RuntimeError):
    """Explains why the optional background-removal feature is unavailable."""


class BackgroundRemovalProcessor(FrameProcessor):

    def __init__(self, model_name: str = "u2net"):
        import threading
        self.lock = threading.Lock()
        try:
            import os
            import glob
            import sys
            # Find nvidia packages in site-packages and add their bin dirs to DLL search path (Python 3.8+ Windows)
            site_packages = [p for p in sys.path if "site-packages" in p]
            for site_dir in site_packages:
                nvidia_bins = glob.glob(os.path.join(site_dir, "nvidia", "*", "bin"))
                for bin_dir in nvidia_bins:
                    if hasattr(os, "add_dll_directory"):
                        os.add_dll_directory(bin_dir)
                    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            from rembg import new_session
        except ImportError as error:
            raise BackgroundRemovalInitializationError(
                "Background removal requires rembg. Run: "
                "python -m pip install rembg onnxruntime"
            ) from error

        self.model_name = model_name
        self.sam_prompt = None
        try:
            self._load_session(model_name)
        except Exception as error:
            raise BackgroundRemovalInitializationError(
                f"Could not load the {model_name} background-removal model. "
                "Check your internet connection for the first download, then "
                f"restart the app. Details: {error}"
            ) from error

    def _load_session(self, model_name: str):
        from rembg import new_session
        providers = self._resolve_providers()
        self.device_label = "GPU" if "CUDAExecutionProvider" in providers else "CPU"
        self._session = new_session(model_name, providers=providers)
        
    def set_model(self, model_name: str):
        """Dynamically switch the active AI model."""
        if self.model_name == model_name:
            return
        self.model_name = model_name
        try:
            self._load_session(model_name)
        except Exception as error:
            print(f"Error loading {model_name}: {error}")

    @property
    def active_provider(self) -> str:
        if hasattr(self, "_session") and self._session is not None:
            if hasattr(self._session, "inner_session"):
                providers = self._session.inner_session.get_providers()
                if providers:
                    return providers[0]
        return "Unknown"

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
        import cv2

        try:
            h, w = frame.shape[:2]
            max_dim = 1920  # 1080p equivalent max dimension

            scale = 1.0
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)

            if scale < 1.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                small_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                rgb_small = small_frame[:, :, ::-1]
                if self.sam_prompt:
                    import copy
                    scaled_prompt = copy.deepcopy(self.sam_prompt)
                    for prompt in scaled_prompt:
                        if prompt['type'] in ('point', 'rectangle'):
                            prompt['data'] = [int(v * scale) for v in prompt['data']]
                    with self.lock:
                        rgba_small = remove(rgb_small, session=self._session, sam_prompt=scaled_prompt)
                else:
                    with self.lock:
                        rgba_small = remove(rgb_small, session=self._session)
                
                # Extract alpha mask and scale back
                alpha_small = rgba_small[:, :, 3]
                alpha_large = cv2.resize(alpha_small, (w, h), interpolation=cv2.INTER_LINEAR)
                
                rgb_frame = frame[:, :, ::-1]
                return np.concatenate([rgb_frame, alpha_large[..., np.newaxis]], axis=2)
            else:
                rgb_frame = frame[:, :, ::-1]
                if self.sam_prompt:
                    with self.lock:
                        return remove(rgb_frame, session=self._session, sam_prompt=self.sam_prompt)
                with self.lock:
                    return remove(rgb_frame, session=self._session)
        except Exception as e:
            # Preserve video playback if one frame fails to process.
            h, w = frame.shape[:2]
            rgb_frame = frame[:, :, ::-1]
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
            return np.concatenate([rgb_frame, alpha], axis=2)
