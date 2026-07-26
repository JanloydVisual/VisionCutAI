"""
Background-removal processor using rembg and ONNX Runtime.
"""

import math
import threading

import numpy as np

from core.frame_processor import FrameProcessor


# Sprint P1: thread-local sidecar so patched_sam_predict can return every
# raw candidate alpha to BackgroundRemovalProcessor.process() without
# modifying rembg's public `remove()` API.  patched_sam_predict populates
# this before returning; process() reads it immediately after remove() exits.
_sam_candidate_sidecar = threading.local()


def patched_sam_predict(self, img, *args, **kwargs):
    from PIL import Image
    import numpy as np
    import cv2
    from rembg.sessions.sam import get_input_points, apply_coords, transform_masks, warp_affine

    prompt = kwargs.get("sam_prompt", [{"type": "point", "label": 1, "data": [int(img.width / 2), int(img.height / 2)]}])
    target_size = 1024
    input_size = (684, 1024)
    encoder_input_name = self.encoder.get_inputs()[0].name

    img_rgb = img.convert("RGB")
    cv_image = np.array(img_rgb)
    original_size = cv_image.shape[:2]

    scale_x = input_size[1] / cv_image.shape[1]
    scale_y = input_size[0] / cv_image.shape[0]
    scale = min(scale_x, scale_y)

    transform_matrix = np.array([[scale, 0, 0], [0, scale, 0], [0, 0, 1]])
    cv_image = warp_affine(cv_image, transform_matrix[:2], (input_size[0], input_size[1]))

    encoder_inputs = {encoder_input_name: cv_image.astype(np.float32)}
    encoder_output = self.encoder.run(None, encoder_inputs)
    image_embedding = encoder_output[0]

    input_points, input_labels = get_input_points(prompt)
    onnx_coord = np.concatenate([input_points, np.array([[0.0, 0.0]])], axis=0)[None, :, :]
    onnx_label = np.concatenate([input_labels, np.array([-1])], axis=0)[None, :].astype(np.float32)
    onnx_coord = apply_coords(onnx_coord, input_size, target_size).astype(np.float32)

    onnx_coord = np.concatenate([onnx_coord, np.ones((1, onnx_coord.shape[1], 1), dtype=np.float32)], axis=2)
    onnx_coord = np.matmul(onnx_coord, transform_matrix.T)
    onnx_coord = onnx_coord[:, :, :2].astype(np.float32)

    onnx_mask_input = np.zeros((1, 1, 256, 256), dtype=np.float32)
    onnx_has_mask_input = np.zeros(1, dtype=np.float32)

    decoder_inputs = {
        "image_embeddings": image_embedding,
        "point_coords": onnx_coord,
        "point_labels": onnx_label,
        "mask_input": onnx_mask_input,
        "has_mask_input": onnx_has_mask_input,
        "orig_im_size": np.array(input_size, dtype=np.float32),
    }

    masks, iou_preds, _ = self.decoder.run(None, decoder_inputs)
    inv_transform_matrix = np.linalg.inv(transform_matrix)
    masks = transform_masks(masks, original_size, inv_transform_matrix)

    # Sprint P1: store every raw binary candidate in the thread-local sidecar
    # so BackgroundRemovalProcessor.process() can retrieve them for ranking.
    # We still return only the highest-IoU mask to rembg's post-processing
    # pipeline so nothing downstream of `remove()` needs to change.
    #
    # Sprint P3: use the session-level threshold for binarisation so the
    # benchmark sweep can sweep logit thresholds without reloading the model.
    threshold = getattr(self, '_mask_threshold', 0.0)
    candidate_alphas = []
    for idx in range(masks.shape[1]):
        binary = (masks[0, idx, :, :] > threshold).astype(np.uint8) * 255
        candidate_alphas.append(binary)
    _sam_candidate_sidecar.candidates = candidate_alphas

    # Return the best-IoU candidate to rembg so its RGBA compositing works
    best_idx = int(np.argmax(iou_preds[0]))
    best_binary = candidate_alphas[best_idx]
    mask_rgb = np.stack([best_binary, best_binary, best_binary], axis=2)
    return [Image.fromarray(mask_rgb).convert("L")]


def _fix_sam_session_gpu_providers(session, providers, sam_model='mobile_sam'):
    """
    C2 (Magic Mask roadmap): rembg's SamSession.__init__ constructs its
    encoder/decoder ONNX Runtime sessions WITHOUT ever passing a `providers`
    argument (verified by reading rembg/sessions/sam.py directly). ONNX
    Runtime silently defaults to CPU-only when providers isn't explicitly
    specified, regardless of what GPU providers are actually available or
    were requested via new_session(..., providers=providers) -- that kwarg
    gets swallowed into SamSession's **kwargs and never reaches the actual
    InferenceSession calls. Confirmed this session: the default u2net model
    correctly picks up CUDA, MobileSAM did not -- meaning every interactive
    SAM inference this entire session ran on CPU, not GPU. Rebuild the
    encoder/decoder sessions with the providers explicitly specified.
    """
    import onnxruntime as ort
    try:
        paths = session.__class__.download_models(sam_model=sam_model)
        session.encoder = ort.InferenceSession(str(paths[0]), providers=providers)
        session.decoder = ort.InferenceSession(str(paths[1]), providers=providers)
    except Exception as error:
        print(f"Could not force GPU providers onto the SAM session, staying on whatever rembg picked: {error}")


def _warmup_sam_session(session):
    """
    Fire one throwaway inference immediately after switching to SAM. Now
    that _fix_sam_session_gpu_providers actually puts MobileSAM on the GPU,
    CUDA's one-time kernel-compilation / memory-pool growth cost (measured
    this session: ~6s and a VRAM peak close to this GPU's 4GB ceiling) lands
    on whichever call happens to be first -- better that's this deliberate
    warm-up during the already-expected brief pause when entering target-
    selection mode, than the user's first real stroke. Uses a tiny dummy
    image since patched_sam_predict always resizes to a fixed 684x1024
    internally regardless of input size, so a small image still exercises
    the same kernel-compilation path at minimal extra cost.
    """
    try:
        from PIL import Image
        import numpy as np
        dummy = Image.fromarray(np.zeros((64, 64, 3), dtype=np.uint8))
        session.predict(dummy, sam_prompt=[{"type": "point", "label": 1, "data": [32, 32]}])
    except Exception as error:
        print(f"SAM warm-up call failed (non-fatal, first real inference will just be slower): {error}")


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
        self.quality = "Balanced"
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
        import rembg
        import types

        providers = self._resolve_providers()
        self.device_label = "GPU" if "CUDAExecutionProvider" in providers else "CPU"
        if model_name == "sam":
            self._session = new_session("sam", sam_model='mobile_sam', providers=providers)
        elif model_name == "sam_base":
            self._session = new_session("sam", sam_model='sam_vit_b_01ec64', providers=providers)
        else:
            self._session = new_session(model_name, providers=providers)

        if model_name in ("sam", "sam_base"):
            sam_model_str = 'mobile_sam' if model_name == "sam" else 'sam_vit_b_01ec64'
            _fix_sam_session_gpu_providers(self._session, providers, sam_model=sam_model_str)
            self._session.predict = types.MethodType(patched_sam_predict, self._session)
            # Sprint P3: initialise threshold on the session so patched_sam_predict
            # can read it without touching the global namespace.
            self._session._mask_threshold = 0.0
            _warmup_sam_session(self._session)
        
    def set_quality(self, quality: str):
        with self.lock:
            self.quality = quality

    def set_mask_threshold(self, threshold: float):
        """Sprint P3: set the logit binarisation threshold used by patched_sam_predict.
        Values below 0.0 expand the mask (recover thin/small regions at the cost
        of background leakage); values above 0.0 contract it.
        Only effective when the active model is SAM / MobileSAM.
        """
        with self.lock:
            if hasattr(self, '_session') and self._session is not None:
                self._session._mask_threshold = float(threshold)

    def set_model(self, model_name: str):
        """Dynamically switch the active AI model."""
        with self.lock:
            if model_name != self.model_name:
                try:
                    from rembg import new_session
                    import gc
                    import os
                    import shutil
                    
                    # Delete old session to free VRAM immediately before loading the new one
                    self._session = None
                    gc.collect()
                    
                    if model_name == "sam":
                        # Ensure MobileSAM decoder exists by copying the standard SAM decoder
                        u2net_home = os.path.expanduser('~/.u2net')
                        os.makedirs(u2net_home, exist_ok=True)
                        mobile_decoder = os.path.join(u2net_home, 'mobile_sam.decoder.onnx')
                        if not os.path.exists(mobile_decoder):
                            sam_decoder = os.path.join(u2net_home, 'sam_vit_b_01ec64.decoder.onnx')
                    if model_name == "sam" or model_name == "sam_base":
                        from rembg import new_session
                        
                        # Load SAM using rembg
                        resolved_providers = self._resolve_providers()
                        sam_model_str = 'mobile_sam' if model_name == "sam" else 'sam_vit_b_01ec64'
                        self._session = new_session("sam", sam_model=sam_model_str, providers=resolved_providers)
                        _fix_sam_session_gpu_providers(self._session, resolved_providers, sam_model=sam_model_str)

                        # Bug fix (Sprint 32B): this branch used to leave the
                        # session's predict() as rembg's stock SAM implementation
                        # -- only _load_session() (called once, at __init__, with
                        # the default "u2net") bound patched_sam_predict. Since
                        # every real interactive-tracking session switches TO
                        # "sam" via this method, patched_sam_predict's fixes (use
                        # only the highest-IoU mask instead of unioning all of
                        # SAM's candidate masks, and filter scattered small
                        # false-positive components) were never actually running.
                        import types
                        self._session.predict = types.MethodType(patched_sam_predict, self._session)
                        # Sprint P3: propagate current threshold to the new session
                        current_threshold = getattr(
                            self._session, '_mask_threshold', 0.0
                        ) if self._session else 0.0
                        self._session._mask_threshold = current_threshold
                        _warmup_sam_session(self._session)
                    else:
                        self._session = new_session(model_name, providers=self._resolve_providers())

                    self.model_name = model_name
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
    def _resolve_providers() -> list:
        """Resolve the best available ONNX Runtime providers."""
        providers = []
        try:
            import onnxruntime as ort
            available = ort.get_available_providers()
            if 'CUDAExecutionProvider' in available:
                providers.append('CUDAExecutionProvider')
            elif 'DmlExecutionProvider' in available:
                providers.append('DmlExecutionProvider')
            else:
                providers.append('CPUExecutionProvider')
        except ImportError:
            providers = ['CPUExecutionProvider']
        return providers

    def process(self, frame, custom_prompt=None, quality_override=None):
        """
        frame: BGR numpy array from VideoEngine.
        quality_override: if set, use this quality preset for this call only
            instead of self.quality, without touching the shared setting.
            Used to run the interactive live-prompt call at higher fidelity
            than the offline render-cache pass without forcing both onto the
            same preset (see AppController._dispatch_regenerate).
        returns: RGBA numpy array for the processed preview.
        """
        from rembg import remove
        import cv2
        import time

        try:
            h, w = frame.shape[:2]

            if quality_override is not None:
                quality_mode = quality_override
            else:
                with self.lock:
                    quality_mode = self.quality

            # Quality presets are a target scale ratio PLUS a hard pixel cap.
            # The cap is what protects small-VRAM GPUs (e.g. a 4GB laptop
            # card): a fixed ratio alone still lets a 4K source run MobileSAM
            # at ~2-3x the intended resolution, which is enough to OOM.
            if quality_mode == "Draft":
                ratio_cap, max_dim = 0.5, 540
            elif quality_mode == "Balanced":
                ratio_cap, max_dim = 0.75, 1080
            else:  # Best
                ratio_cap, max_dim = 1.0, 4000

            proxy_scale = ratio_cap
            if max(h, w) * proxy_scale > max_dim:
                proxy_scale = max_dim / max(h, w)

            start_time = time.perf_counter()

            rgb_frame = frame[:, :, ::-1]
            if proxy_scale < 1.0:
                h, w = frame.shape[:2]
                new_w, new_h = int(w * proxy_scale), int(h * proxy_scale)
                rgb_small = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
                # Prompts are already scaled and flattened by InferencePromptAdapter
                active_prompt = custom_prompt if custom_prompt is not None else self.sam_prompt
                if active_prompt:
                    print(f"[DEBUG] Processing {quality_mode} scale SAM prompt with {len(active_prompt)} points")
                    # Clear sidecar before inference so a stale value is never used
                    _sam_candidate_sidecar.candidates = None
                    with self.lock:
                        rgba_result = remove(rgb_small, session=self._session, sam_prompt=active_prompt)

                    # Retrieve all raw candidates written by patched_sam_predict
                    raw_candidates = getattr(_sam_candidate_sidecar, 'candidates', None)
                    if raw_candidates and len(raw_candidates) > 1:
                        # Scale every candidate alpha back to full resolution
                        scaled_candidates = []
                        for raw_alpha in raw_candidates:
                            alpha_large = cv2.resize(raw_alpha, (w, h), interpolation=cv2.INTER_LINEAR)
                            scaled_candidates.append(
                                np.concatenate([rgb_frame, alpha_large[..., np.newaxis]], axis=2)
                            )
                        return scaled_candidates
                    else:
                        # Fallback: single RGBA from rembg
                        alpha_small = rgba_result[:, :, 3]
                        alpha_large = cv2.resize(alpha_small, (w, h), interpolation=cv2.INTER_LINEAR)
                        return [np.concatenate([rgb_frame, alpha_large[..., np.newaxis]], axis=2)]
                else:
                    with self.lock:
                        rgba_result = remove(rgb_small, session=self._session)
                    alpha_small = rgba_result[:, :, 3]
                    alpha_large = cv2.resize(alpha_small, (w, h), interpolation=cv2.INTER_LINEAR)
                    return [np.concatenate([rgb_frame, alpha_large[..., np.newaxis]], axis=2)]
            else:
                active_prompt = custom_prompt if custom_prompt is not None else self.sam_prompt
                if active_prompt:
                    print(f"[DEBUG] Processing full scale SAM prompt with {len(active_prompt)} points")
                    _sam_candidate_sidecar.candidates = None
                    with self.lock:
                        rgba_result = remove(rgb_frame, session=self._session, sam_prompt=active_prompt)

                    raw_candidates = getattr(_sam_candidate_sidecar, 'candidates', None)
                    if raw_candidates and len(raw_candidates) > 1:
                        result_list = []
                        for raw_alpha in raw_candidates:
                            result_list.append(
                                np.concatenate([rgb_frame, raw_alpha[..., np.newaxis]], axis=2)
                            )
                        return result_list
                    else:
                        return [np.concatenate([rgb_frame, rgba_result[:, :, 3][..., np.newaxis]], axis=2)]
                else:
                    with self.lock:
                        rgba_result = remove(rgb_frame, session=self._session)
                    return [np.concatenate([rgb_frame, rgba_result[:, :, 3][..., np.newaxis]], axis=2)]

            end_time = time.perf_counter()
            inference_time_ms = (end_time - start_time) * 1000
            preview_fps = 1000.0 / inference_time_ms if inference_time_ms > 0 else 0
            
            input_res_h = int(h * proxy_scale)
            print(f"--- Diagnostics ---")
            print(f"AI Preview Mode: {quality_mode}")
            print(f"AI Input Resolution: {input_res_h}p")
            print(f"Inference Time: {inference_time_ms:.1f} ms")
            print(f"Preview FPS: {preview_fps:.1f}")
            print(f"-------------------")
            
        except Exception as e:
            # Preserve video playback if one frame fails to process.
            h, w = frame.shape[:2]
            rgb_frame = frame[:, :, ::-1]
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
            return [np.concatenate([rgb_frame, alpha], axis=2)]
