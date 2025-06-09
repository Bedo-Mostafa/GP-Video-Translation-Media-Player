import threading

from typing import Optional
from services.audio.audio_processing import extract_raw_audio_to_numpy

from services.config.context import ProcessingContext
from services.utils.aspect import performance_log
from utils.logging_config import get_component_logger

logger = get_component_logger("video_processor")


class AudioPreprocessor:
    """Simplified audio preprocessor, mainly for raw audio extraction."""

    @staticmethod
    @performance_log
    def load_raw_audio_into_context(
        context: ProcessingContext, cancel_event: Optional[threading.Event] = None
    ) -> None:
        """Extracts raw audio into context.audio_data_np."""
        logger.info(f"Task {context.task_id}: Loading raw audio into context.")
        context.audio_data_np, context.sample_rate = extract_raw_audio_to_numpy(
            context.video_path, context.start_from
        )

        if context.audio_data_np is None or context.sample_rate is None:
            if not (cancel_event and cancel_event.is_set()):
                logger.error(f"Task {context.task_id}: Failed to load raw audio data.")
                raise ValueError("Failed to load raw audio data for processing.")
            else:
                logger.info(f"Task {context.task_id}: Raw audio loading cancelled.")
        else:
            logger.info(
                f"Task {context.task_id}: Raw audio loaded. Shape: {context.audio_data_np.shape}, SR: {context.sample_rate}"
            )
