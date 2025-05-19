import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Generate log filename with timestamp
LOG_FILENAME = LOGS_DIR / f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Name of the logger
        level: Logging level (default: INFO)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Create formatters
    console_formatter = logging.Formatter(LOG_FORMAT)
    file_formatter = logging.Formatter(DETAILED_LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    return logger

# Create loggers for different components
def get_audio_logger() -> logging.Logger:
    """Get logger for audio processing components."""
    return setup_logger("audio_processor")

def get_model_logger() -> logging.Logger:
    """Get logger for model operations."""
    return setup_logger("model_loader")

def get_api_logger() -> logging.Logger:
    """Get logger for API operations."""
    return setup_logger("api")

def get_transcription_logger() -> logging.Logger:
    """Get logger for transcription operations."""
    return setup_logger("transcription")

def get_translation_logger() -> logging.Logger:
    """Get logger for translation operations."""
    return setup_logger("translation")

def get_processor_logger() -> logging.Logger:
    """Get logger for video processing operations."""
    return setup_logger("video_processor")

# Main application logger
app_logger = setup_logger("transcription_app") 