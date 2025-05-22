from asyncio.log import logger
import os
from typing import List
import numpy as np  # Added for type hint

from faster_whisper import WhisperModel  #


def transcribe_segment(
    model: WhisperModel, audio_input: np.ndarray, start_time: float, end_time: float
) -> List[dict]:
    try:
        segments, info = model.transcribe(
            audio_input,
            language="en",
            beam_size=5,
            no_speech_threshold=0.5,
            word_timestamps=True,
        )
        adjusted_segments = []
        for segment in segments:
            segment_start_abs = max(segment.start + start_time, start_time)
            segment_end_abs = min(segment.end + start_time, end_time)
            if segment_start_abs < segment_end_abs:
                adjusted_segments.append(
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                    }
                )
        return adjusted_segments
    except Exception as e:
        logger.error(f"Error transcribing segment: {e}", exc_info=True)
        return []
