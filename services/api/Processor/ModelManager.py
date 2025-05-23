from services.utils.aspect import performance_log
from services.models.model_config import ModelConfig
from services.models.model_loader import load_whisper_model
from services.utils.logging_config import get_processor_logger

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
