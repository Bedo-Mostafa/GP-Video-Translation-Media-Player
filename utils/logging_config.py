import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
import glob
import os
from typing import Optional

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Log formats
CONSOLE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DETAILED_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: [%(filename)s:%(lineno)d] - %(message)s"

def cleanup_old_logs(prefix: str, keep_count: int = 3):
    """Clean up old log files, keeping only the most recent ones."""
    pattern = str(LOGS_DIR / f"{prefix}*.log")
    log_files = sorted(glob.glob(pattern), key=os.path.getctime, reverse=True)
    
    # Remove old log files
    for old_file in log_files[keep_count:]:
        try:
            os.remove(old_file)
        except Exception as e:
            print(f"Error removing old log file {old_file}: {e}")

def setup_logging():
    """Configure logging for the application."""
    # Clean up old logs before setting up new logging
    cleanup_old_logs("app_")
    cleanup_old_logs("transcription_")
    
    # Create formatters
    console_formatter = logging.Formatter(
        CONSOLE_FORMAT,
        datefmt="%H:%M:%S"
    )
    file_formatter = logging.Formatter(
        FILE_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    detailed_formatter = logging.Formatter(
        DETAILED_FILE_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # App file handler
    app_log_filename = LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    app_file_handler = logging.handlers.RotatingFileHandler(
        app_log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=2,
        encoding='utf-8'
    )
    app_file_handler.setFormatter(file_formatter)
    app_file_handler.setLevel(logging.DEBUG)
    
    # Transcription file handler
    transcription_log_filename = LOGS_DIR / f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    transcription_file_handler = logging.handlers.RotatingFileHandler(
        transcription_log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=2,
        encoding='utf-8'
    )
    transcription_file_handler.setFormatter(detailed_formatter)
    transcription_file_handler.setLevel(logging.DEBUG)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = []  # Remove existing handlers
    root_logger.addHandler(console_handler)
    
    # Create and configure component loggers
    app_logger = logging.getLogger("VideoPlayerApp")
    app_logger.addHandler(app_file_handler)
    
    # Service loggers
    service_loggers = [
        "audio_processor",
        "model_loader",
        "api",
        "transcription",
        "translation",
        "video_processor",
        "transcription_app"
    ]
    
    for logger_name in service_loggers:
        logger = logging.getLogger(logger_name)
        logger.addHandler(transcription_file_handler)
    
    return app_logger

def get_component_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger for a specific component.
    
    Args:
        name: Name of the component/logger
        level: Optional logging level override
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger
