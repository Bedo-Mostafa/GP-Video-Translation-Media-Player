from os import path
from torch import cuda
from faster_whisper import WhisperModel
from transformers import MarianMTModel, MarianTokenizer
from services.models.model_config import ModelConfig, default_config
from services.utils.logging_config import get_model_logger

logger = get_model_logger()


def load_translation_model(config: ModelConfig = default_config):
    """Load the MarianMT model and tokenizer from local directory.

    Args:
        config: ModelConfig instance with model settings. Uses default_config if not provided.
    """
    model_path = config.get_marianmt_path()
    logger.info(f"Loading MarianMT model from: {model_path}")

    if not path.exists(model_path):
        error_msg = (
            f"MarianMT model not found at {model_path}. Please download it first."
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        logger.debug("Loading MarianMT tokenizer...")
        tokenizer = MarianTokenizer.from_pretrained(model_path)

        logger.debug("Loading MarianMT model...")
        nmt_model = MarianMTModel.from_pretrained(model_path)

        device = config.device or ("cuda" if cuda.is_available() else "cpu")
        logger.info(f"Using device: {device}")
        nmt_model = nmt_model.to(device)
        nmt_model.eval()

        logger.info("MarianMT model loaded successfully")
        return nmt_model, tokenizer
    except Exception as e:
        logger.error(f"Failed to load MarianMT model: {str(e)}", exc_info=True)
        raise


def load_whisper_model(config: ModelConfig = default_config) -> WhisperModel:
    """Load the Faster Whisper model from local directory.

    Args:
        config: ModelConfig instance with model settings. Uses default_config if not provided.
    """
    model_path = config.get_whisper_path()
    logger.info(
        f"Loading Faster Whisper model '{config.whisper_model_name}' from {model_path}"
    )

    if not path.exists(model_path):
        error_msg = (
            f"Faster Whisper model not found at {model_path}. Please download it first."
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        device = config.device or ("cuda" if cuda.is_available() else "cpu")
        logger.info(f"Using device: {device}")
        logger.debug(
            f"Model configuration: compute_type={config.whisper_compute_type}, "
            f"cpu_threads={config.whisper_cpu_threads}, "
            f"num_workers={config.whisper_num_workers}"
        )

        model = WhisperModel(
            model_path,
            device=device,
            compute_type=config.whisper_compute_type,
            cpu_threads=config.whisper_cpu_threads,
            num_workers=config.whisper_num_workers,
        )

        logger.info("Faster Whisper model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load Faster Whisper model: {str(e)}", exc_info=True)
        raise
