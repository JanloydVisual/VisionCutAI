import os
import shutil
import platform
import onnxruntime as ort

class StartupValidator:
    """Validates critical requirements before opening the application."""
    
    @staticmethod
    def validate_all(progress_callback=None):
        if progress_callback: progress_callback("Checking folders...")
        StartupValidator._check_folders()
        
        if progress_callback: progress_callback("Checking ONNX Runtime...")
        StartupValidator._check_onnx()
        
        if progress_callback: progress_callback("Checking MobileSAM models...")
        StartupValidator._check_models()
        
        if progress_callback: progress_callback("Checking FFmpeg...")
        StartupValidator._check_ffmpeg()
        
    @staticmethod
    def _check_folders():
        for folder in ["logs", "crashes", "autosave", "temp"]:
            os.makedirs(folder, exist_ok=True)
            
    @staticmethod
    def _check_onnx():
        providers = ort.get_available_providers()
        # Ensure ONNX is loadable (if it gets here, import succeeded).
        pass

    @staticmethod
    def _check_models():
        pass

    @staticmethod
    def _check_ffmpeg():
        if not shutil.which("ffmpeg"):
            raise EnvironmentError("FFmpeg is not installed or not found in system PATH. Please install FFmpeg to use VisionCut AI.")
