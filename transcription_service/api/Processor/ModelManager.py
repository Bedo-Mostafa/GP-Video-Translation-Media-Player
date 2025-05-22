# AudioSegment dataclass is no longer needed as Whisper yields its own segment structure


from transcription_service.api.VideoProcessor import logger
from transcription_service.models.model_config import ModelConfig
from transcription_service.models.model_loader import load_whisper_model
from transcription_service.utils.aspect import performance_log


class ModelManager:
    # [Code from your existing VideoProcessor.py - unchanged]
    def __init__(self):
        self.whisper_model = None
        self.current_config = None

    @performance_log
    def get_model(self, config: ModelConfig):
        if self.whisper_model is None or self.current_config != config:
            logger.info(f"Loading transcription model with config: {config}")
            self.whisper_model = load_whisper_model(config)
            self.current_config = config
            logger.info("Transcription model loaded successfully")
        else:
            logger.debug("Using cached transcription model")
        return self.whisper_model