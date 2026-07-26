import cv2
import numpy as np
from typing import Optional, Union, Tuple
from core.render.preview_mode import PreviewMode

class BackgroundSource:
    ORIGINAL = "original"
    SOLID_COLOR = "solid_color"
    IMAGE = "image"
    BLURRED_ORIGINAL = "blurred_original"

class Compositor:
    """
    Compositing layer that combines the AI-extracted foreground with different background sources.
    """
    def __init__(self):
        self.bg_type = BackgroundSource.SOLID_COLOR
        self.bg_color = (0, 255, 0)  # Green screen by default
        self.bg_image: Optional[np.ndarray] = None
        self.blur_radius = 21

    def set_background_solid(self, color: Tuple[int, int, int]):
        self.bg_type = BackgroundSource.SOLID_COLOR
        self.bg_color = color
        
    def set_background_image(self, image_path: str):
        self.bg_type = BackgroundSource.IMAGE
        img = cv2.imread(image_path)
        if img is not None:
            self.bg_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
    def set_background_blurred(self, radius: int = 21):
        self.bg_type = BackgroundSource.BLURRED_ORIGINAL
        self.blur_radius = radius
        
    def set_background_original(self):
        self.bg_type = BackgroundSource.ORIGINAL

    def composite(self, frame: np.ndarray, alpha_mask: np.ndarray, mode: PreviewMode = PreviewMode.BALANCED) -> np.ndarray:
        """
        Composites the frame using the alpha_mask over the configured background.
        alpha_mask should be a single-channel image (0-255).
        """
        h, w = frame.shape[:2]
        
        # 1. Generate Background Layer
        bg = np.zeros_like(frame)
        if self.bg_type == BackgroundSource.SOLID_COLOR:
            bg[:] = self.bg_color
        elif self.bg_type == BackgroundSource.IMAGE and self.bg_image is not None:
            bg = cv2.resize(self.bg_image, (w, h))
        elif self.bg_type == BackgroundSource.BLURRED_ORIGINAL:
            bg = cv2.GaussianBlur(frame, (self.blur_radius, self.blur_radius), 0)
        else: # ORIGINAL
            bg = frame.copy()
            
        # FAST mode: simple binary composite
        if mode == PreviewMode.FAST:
            binary_mask = (alpha_mask > 127).astype(np.uint8)
            binary_mask_3d = np.repeat(binary_mask[:, :, np.newaxis], 3, axis=2)
            return np.where(binary_mask_3d == 1, frame, bg)

        # BALANCED / FINAL modes: True alpha compositing
        alpha = alpha_mask.astype(float) / 255.0
        alpha_3d = np.repeat(alpha[:, :, np.newaxis], 3, axis=2)
        
        frame_f = frame.astype(float)
        bg_f = bg.astype(float)
        
        composited = frame_f * alpha_3d + bg_f * (1.0 - alpha_3d)
        return np.clip(composited, 0, 255).astype(np.uint8)
