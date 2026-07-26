import sys
import os
import faulthandler
import datetime
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox

# Catch C++ segfaults and write to crash logs
os.makedirs("crashes", exist_ok=True)
crash_log_path = os.path.join("crashes", f"segfault_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
crash_log = open(crash_log_path, 'w')
faulthandler.enable(file=crash_log)

from version import __version__
from ui.main_window import MainWindow
from ui.splash_screen import ModernSplashScreen
from core.validator import StartupValidator
from ui.error_dialog import ErrorDialog

_main_window = None

def global_excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(os.path.abspath("crashes"), f"crash_{timestamp}.log")
    
    try:
        import platform
        import psutil
        import subprocess
        import onnxruntime as ort
        
        gpu_model = "N/A"
        vram_usage = "N/A"
        try:
            res = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.used", "--format=csv,noheader"],
                encoding="utf-8", stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW
            ).strip()
            if res:
                parts = res.split(",")
                if len(parts) >= 2:
                    gpu_model = parts[0].strip()
                    vram_usage = parts[1].strip()
        except:
            pass
            
        cuda_version = "N/A"
        try:
            res = subprocess.check_output(
                ["nvcc", "--version"],
                encoding="utf-8", stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in res.splitlines():
                if "release" in line:
                    cuda_version = line.split("release")[-1].strip()
        except:
            pass

        proj_path = "N/A"
        video_path = "N/A"
        frame = "N/A"
        tracking_status = "N/A"
        cache_status = "N/A"
        
        global _main_window
        if _main_window and hasattr(_main_window, 'controller'):
            ctrl = _main_window.controller
            if hasattr(ctrl, 'project'):
                proj_path = getattr(ctrl.project, 'path', 'Unsaved')
            if hasattr(ctrl, 'video') and ctrl.video.is_loaded:
                # Safely try to get video path
                if hasattr(ctrl.video, 'decoder') and ctrl.video.decoder:
                    video_path = getattr(ctrl.video.decoder, '_filepath', getattr(ctrl.video.decoder, 'filepath', 'N/A'))
            
            if hasattr(ctrl, 'video') and ctrl.video:
                frame = getattr(ctrl.video, 'current_frame_index', 'N/A')
            if hasattr(ctrl, 'tracking_engine'):
                tracking_status = "Active" if ctrl.tracking_engine._is_running else "Idle"
            if hasattr(ctrl, 'render_cache'):
                try:
                    cache_status = f"{len(list(ctrl.render_cache.cache_dir.glob('*.png')))} frames"
                except:
                    pass

        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        
        report = []
        report.append(f"--- VisionCut AI Crash Report ---")
        report.append(f"Timestamp: {timestamp}")
        report.append(f"VisionCut AI version: {__version__}")
        report.append(f"Build number: {__version__}")
        report.append(f"Python version: {sys.version}")
        report.append(f"Windows version: {platform.system()} {platform.release()} ({platform.version()})")
        report.append(f"GPU model: {gpu_model}")
        report.append(f"CUDA version: {cuda_version}")
        report.append(f"ONNX Runtime version: {ort.__version__}")
        report.append(f"Current project path: {proj_path}")
        report.append(f"Current video path: {video_path}")
        report.append(f"Current timeline frame: {frame}")
        report.append(f"Tracking status: {tracking_status}")
        report.append(f"Render cache status: {cache_status}")
        report.append(f"RAM usage: {ram.used / (1024**3):.2f} GB / {ram.total / (1024**3):.2f} GB")
        report.append(f"VRAM usage: {vram_usage}")
        report.append(f"CPU usage: {cpu}%")
        report.append(f"Exception type: {exc_type.__name__}")
        report.append(f"Exception message: {str(exc_value)}")
        report.append(f"\n--- Full traceback ---")
        report.append("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
            
    except Exception as fallback_e:
        # Fallback if telemetry gathering crashes
        with open(log_path, "w") as f:
            f.write(f"CRASH REPORT GENERATION FAILED: {str(fallback_e)}\n\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        
    dialog = ErrorDialog("VisionCut AI - Fatal Error", 
                         "A critical error occurred. A crash report has been saved.", 
                         (exc_type, exc_value, exc_traceback), log_path)
    dialog.exec()
    sys.exit(1)

def main():
    sys.excepthook = global_excepthook
    
    app = QApplication(sys.argv)
    
    from ui.theme import get_stylesheet
    app.setStyleSheet(get_stylesheet())    
    splash = ModernSplashScreen(__version__)
    splash.show()
    
    try:
        StartupValidator.validate_all(progress_callback=splash.set_progress)
    except Exception as e:
        splash.hide()
        QMessageBox.critical(None, "Startup Error", str(e))
        sys.exit(1)
        
    splash.set_progress("Preparing UI...", delay=0.2)
    
    is_dev = os.environ.get("VISIONCUT_ENV") == "development"
    global _main_window
    _main_window = MainWindow(is_dev=is_dev)
    _main_window.show()
    
    splash.finish(_main_window)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()