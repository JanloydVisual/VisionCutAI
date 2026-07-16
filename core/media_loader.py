"""
MediaLoader
-----------
Detects media type and dispatches to appropriate loader.
Supports: videos, images, and extensible for future formats.
"""

import os
from pathlib import Path


# Supported file extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}


def detect_media_type(filepath: str) -> str:
    """
    Detect the media type based on file extension.
    
    Returns:
        'image', 'video', or 'unknown'
    """
    ext = Path(filepath).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'unknown'


def is_image(filepath: str) -> bool:
    """Check if the file is a supported image format."""
    return detect_media_type(filepath) == 'image'


def is_video(filepath: str) -> bool:
    """Check if the file is a supported video format."""
    return detect_media_type(filepath) == 'video'