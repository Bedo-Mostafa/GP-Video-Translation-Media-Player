from asyncio.log import logger
import numpy as np

from faster_whisper import WhisperModel

from typing import Generator
from services.utils.aspect import performance_log


@performance_log
def transcribe_segment(
    model: WhisperModel,
    language: str,
    audio_input: np.ndarray,
    start_time: float,
    end_time: float,
) -> Generator[dict, None, None]:
    try:
        segments, _ = model.transcribe(
            audio_input,
            language=language,
            beam_size=1,
            no_speech_threshold=0.5,
            word_timestamps=True,
        )
        for segment in segments:
            segment_start_abs = max(segment.start + start_time, start_time)
            segment_end_abs = min(segment.end + start_time, end_time)
            if segment_start_abs < segment_end_abs:
                yield {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
    except Exception as e:
        logger.error(f"Error transcribing segment: {e}", exc_info=True)
        return
