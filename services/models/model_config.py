from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelConfig:
    """Configuration class for model settings and paths."""

    # Base directory for all models
    models_base_dir: str = "services\models"

    # MarianMT model settings
    marianmt_model_name: str = "marianmt_en_ar_distilled"

    # Whisper model settings
    whisper_model_name: str = "small"
    whisper_compute_type: str = "int8"
    whisper_cpu_threads: int = 2
    whisper_num_workers: int = 2

    # Device settings
    device: Optional[str] = None  # If None, will be automatically determined

    def get_marianmt_path(self) -> str:
        """Get the full path for MarianMT model."""
        return f"{self.models_base_dir}/{self.marianmt_model_name}"

    def get_whisper_path(self) -> str:
        """Get the full path for Whisper model."""
        return f"{self.models_base_dir}/faster_whisper_{self.whisper_model_name}"


# Default configuration instance
default_config = ModelConfig()
