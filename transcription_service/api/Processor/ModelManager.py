# AudioSegment dataclass is no longer needed as Whisper yields its own segment structure


from transcription_service.utils.logging_config import get_processor_logger

from transcription_service.models.model_config import ModelConfig
from transcription_service.models.model_loader import load_whisper_model
from transcription_service.utils.aspect import performance_log

logger = get_processor_logger()


class ModelManager:
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
