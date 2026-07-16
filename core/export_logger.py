"""
Export Logger
-------------
Creates and manages export.log and error.log in a logs folder.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


class ExportLogger:
    """
    Manages application logging with separate export and error log files.
    """

    _export_logger = None
    _error_logger = None
    _logs_dir = None

    @classmethod
    def initialize(cls, logs_dir: str = None):
        """Initialize logging system. Creates logs directory if needed."""
        if logs_dir:
            cls._logs_dir = logs_dir
        else:
            cls._logs_dir = os.path.join(os.getcwd(), "logs")

        os.makedirs(cls._logs_dir, exist_ok=True)

        # Create export logger
        cls._export_logger = logging.getLogger("VisionCutAI.export")
        cls._export_logger.setLevel(logging.INFO)
        cls._export_logger.handlers.clear()

        export_handler = RotatingFileHandler(
            os.path.join(cls._logs_dir, "export.log"),
            maxBytes=1024 * 1024,  # 1MB
            backupCount=3
        )
        export_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        ))
        cls._export_logger.addHandler(export_handler)

        # Create error logger
        cls._error_logger = logging.getLogger("VisionCutAI.error")
        cls._error_logger.setLevel(logging.ERROR)
        cls._error_logger.handlers.clear()

        error_handler = RotatingFileHandler(
            os.path.join(cls._logs_dir, "error.log"),
            maxBytes=1024 * 1024,  # 1MB
            backupCount=3
        )
        error_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        ))
        cls._error_logger.addHandler(error_handler)

        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        ))
        cls._export_logger.addHandler(console_handler)

        cls.info("Logging initialized")

    @classmethod
    def info(cls, message: str):
        """Log info message to export log."""
        if cls._export_logger is None:
            cls.initialize()
        cls._export_logger.info(message)

    @classmethod
    def warning(cls, message: str):
        """Log warning to export log."""
        if cls._export_logger is None:
            cls.initialize()
        cls._export_logger.warning(message)

    @classmethod
    def error(cls, message: str, exception: Exception = None):
        """Log error to both logs."""
        if cls._export_logger is None:
            cls.initialize()
        if cls._error_logger:
            if exception:
                cls._error_logger.exception(message)
            else:
                cls._error_logger.error(message)
        cls._export_logger.error(message)

    @classmethod
    def get_logs_dir(cls) -> str:
        """Return the logs directory path."""
        if cls._logs_dir is None:
            cls.initialize()
        return cls._logs_dir

    @classmethod
    def log_export_start(cls, output_path: str, media_path: str):
        """Log export start event."""
        cls.info(f"Export started | Output: {output_path} | Media: {media_path}")

    @classmethod
    def log_export_progress(cls, frame: int, total: int):
        """Log export progress."""
        cls.info(f"Export progress | Frame: {frame}/{total}")

    @classmethod
    def log_export_complete(cls, output_path: str, frame_count: int):
        """Log export completion."""
        cls.info(f"Export complete | Output: {output_path} | Frames: {frame_count}")

    @classmethod
    def log_export_error(cls, error: str):
        """Log export error."""
        cls.error(f"Export error | {error}")