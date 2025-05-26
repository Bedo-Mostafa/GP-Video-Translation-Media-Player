from subprocess import CalledProcessError, Popen, run, PIPE
import numpy as np
from typing import Optional

from services.utils.aspect import performance_log
from utils.logging_config import get_component_logger

logger = get_component_logger("audio_processor")


@performance_log
def get_video_duration(video_path: str) -> float:
    logger.debug(f"Getting duration for video: {video_path}")
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        video_path,
    ]
    try:
        result = run(cmd, stdout=PIPE, text=True, check=True)
        duration = float(result.stdout.strip())
        logger.debug(f"Video duration: {duration} seconds")
        return duration
    except CalledProcessError as e:
        logger.error(f"FFprobe failed: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error(
            "FFprobe not found. Please ensure FFmpeg is installed and added to your PATH."
        )
        raise

@performance_log
def extract_raw_audio_to_numpy(
    video_path: str,
) -> tuple[Optional[np.ndarray], Optional[int]]:
    """
    Extracts raw audio from a video file using ffmpeg and returns it as a NumPy array.
    No cleaning or other processing is done here.
    """
    logger.info(f"Extracting raw audio from video to NumPy array: {video_path}")
    extract_cmd = [
        "ffmpeg",
        "-y",
        "-threads", "0",
        "-hwaccel", "auto",
        "-i", video_path,
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # Output PCM 16-bit little-endian
        "-ar", "16000",  # Target sample rate 16kHz (Whisper preferred)
        "-ac", "1",  # Mono channel
        "-af", "aresample=resampler=soxr", # Use SoXR resampler (faster than default)
        "-f", "s16le",  # Output raw s16le PCM
        "pipe:1",  # Output to stdout
    ]
    try:
        process = Popen(extract_cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            logger.error(
                f"FFmpeg failed during raw audio extraction: {stderr.decode()}"
            )
            return None, None

        # Convert raw PCM data to NumPy array
        # s16le means signed 16-bit little-endian integers
        audio_data_int16 = np.frombuffer(stdout, dtype=np.int16)
        # Normalize to float32 range [-1.0, 1.0]
        audio_data_float32 = audio_data_int16.astype(np.float32) / 32768.0
        sample_rate = 16000  # We requested this sample rate from ffmpeg

        logger.info(
            f"Raw audio extracted successfully to NumPy array. Shape: {audio_data_float32.shape}, SR: {sample_rate}Hz"
        )
        return audio_data_float32, sample_rate
    except FileNotFoundError:
        logger.error(
            "FFmpeg not found. Please ensure FFmpeg is installed and added to your PATH."
        )
        raise
    except Exception as e:
        logger.error(f"Error extracting raw audio to NumPy: {str(e)}", exc_info=True)
        return None, None
