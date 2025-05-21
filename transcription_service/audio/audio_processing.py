# import shutil
# import subprocess

# import noisereduce as nr
# import numpy as np
# import soundfile as sf
# import webrtcvad

# from ..utils.aspect import performance_log
# from ..utils.logging_config import get_audio_logger

# logger = get_audio_logger()


# @performance_log
# def get_video_duration(video_path: str) -> float:
#     """Get the duration of a video file using ffprobe."""
#     logger.debug(f"Getting duration for video: {video_path}")
#     cmd = [
#         "ffprobe",
#         "-v",
#         "error",
#         "-show_entries",
#         "format=duration",
#         "-of",
#         "default=noprint_wrappers=1:nokey=1",
#         video_path,
#     ]
#     try:
#         result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
#         duration = float(result.stdout.strip())
#         logger.debug(f"Video duration: {duration} seconds")
#         return duration
#     except subprocess.CalledProcessError as e:
#         logger.error(f"FFprobe failed: {e.stderr}")
#         raise
#     except FileNotFoundError:
#         logger.error(
#             "FFprobe not found. Please ensure FFmpeg is installed and added to your PATH."
#         )
#         raise


# @performance_log
# def extract_audio_from_video(video_path: str, output_path: str) -> str:
#     """Extract audio from a video file using ffmpeg."""
#     logger.info(f"Extracting audio from video: {video_path}")
#     extract_cmd = [
#         "ffmpeg",
#         "-y",
#         "-i",
#         video_path,
#         "-vn",
#         "-acodec",
#         "pcm_s16le",
#         "-ar",
#         "16000",
#         "-ac",
#         "1",
#         output_path,
#     ]
#     try:
#         result = subprocess.run(extract_cmd, check=True, capture_output=True, text=True)
#         logger.info(f"Audio extracted successfully to: {output_path}")
#         return output_path
#     except subprocess.CalledProcessError as e:
#         logger.error(f"FFmpeg failed: {e.stderr}")
#         raise
#     except FileNotFoundError:
#         logger.error(
#             "FFmpeg not found. Please ensure FFmpeg is installed and added to your PATH."
#         )
#         raise


# @performance_log
# def get_speech_mask(
#     audio: np.ndarray, sr: int, frame_duration_ms: int = 30
# ) -> np.ndarray:
#     """Generate a speech mask using WebRTC VAD."""
#     logger.debug(f"Generating speech mask for audio with {len(audio)} samples")
#     vad = webrtcvad.Vad(2)
#     frame_length = int(sr * frame_duration_ms / 1000)
#     padded_audio = np.pad(
#         audio, (0, frame_length - len(audio) % frame_length), mode="constant"
#     )
#     frames = np.reshape(padded_audio, (-1, frame_length))
#     speech_mask = np.zeros(len(audio), dtype=bool)

#     for i, frame in enumerate(frames):
#         byte_data = (frame * 32768).astype(np.int16).tobytes()
#         is_speech = vad.is_speech(byte_data, sample_rate=sr)
#         if is_speech:
#             start = i * frame_length
#             end = min((i + 1) * frame_length, len(audio))
#             speech_mask[start:end] = True

#     speech_percentage = (np.sum(speech_mask) / len(speech_mask)) * 100
#     logger.debug(f"Speech detected in {speech_percentage:.2f}% of the audio")
#     return speech_mask


# @performance_log
# def isolate_speech_focused(audio_path: str, output_speech_path: str) -> str:
#     """Isolate speech from audio by reducing noise."""
#     logger.info(f"Starting speech isolation for: {audio_path}")
#     try:
#         y, sr = sf.read(audio_path)
#         logger.debug(f"Audio loaded: {len(y)} samples at {sr}Hz")

#         if y.ndim > 1:
#             y = np.mean(y, axis=1)
#             logger.debug("Converted stereo to mono")

#         speech_mask = get_speech_mask(y, sr)
#         noise_profile = y[~speech_mask]

#         if len(noise_profile) < 1:
#             logger.warning(
#                 "No noise profile could be generated, falling back to full audio"
#             )
#             noise_profile = y

#         logger.info("Starting noise reduction...")
#         reduced_audio = nr.reduce_noise(
#             y=y,
#             sr=sr,
#             y_noise=noise_profile,
#             stationary=False,
#             prop_decrease=0.8,
#             use_tqdm=True,
#         )

#         sf.write(output_speech_path, reduced_audio, sr)
#         logger.info(
#             f"Speech isolation completed. Output saved to: {output_speech_path}"
#         )
#         return output_speech_path
#     except Exception as e:
#         logger.error(f"Failed to isolate speech: {str(e)}", exc_info=True)
#         return None


# @performance_log
# def prepare_audio(video_path: str, raw_audio_path: str, cleaned_audio_path: str):
#     """Prepare audio by extracting and cleaning it from a video."""
#     logger.info(f"Starting audio preparation for video: {video_path}")
#     try:
#         extract_audio_from_video(video_path, raw_audio_path)
#         result = isolate_speech_focused(raw_audio_path, cleaned_audio_path)

#         if not result:
#             logger.warning("Speech isolation failed. Using original audio instead.")
#             shutil.copy(raw_audio_path, cleaned_audio_path)
#             logger.info(f"Copied original audio to: {cleaned_audio_path}")
#     except Exception as e:
#         logger.error(f"Audio preparation failed: {str(e)}", exc_info=True)
#         raise


import shutil
import subprocess

import noisereduce as nr
import numpy as np
import soundfile as sf
import webrtcvad

from ..utils.aspect import performance_log
from ..utils.logging_config import get_audio_logger

logger = get_audio_logger()


@performance_log
def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file using ffprobe."""
    logger.debug(f"Getting duration for video: {video_path}")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
        duration = float(result.stdout.strip())
        logger.debug(f"Video duration: {duration} seconds")
        return duration
    except subprocess.CalledProcessError as e:
        logger.error(f"FFprobe failed: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error(
            "FFprobe not found. Please ensure FFmpeg is installed and added to your PATH."
        )
        raise


@performance_log
def extract_audio_from_video(video_path: str, output_path: str) -> str:
    """Extract audio from a video file using ffmpeg."""
    logger.info(f"Extracting audio from video: {video_path}")
    extract_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        output_path,
    ]
    try:
        result = subprocess.run(extract_cmd, check=True, capture_output=True, text=True)
        logger.info(f"Audio extracted successfully to: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error(
            "FFmpeg not found. Please ensure FFmpeg is installed and added to your PATH."
        )
        raise


@performance_log
def get_speech_mask(
    audio: np.ndarray, sr: int, frame_duration_ms: int = 30
) -> np.ndarray:
    """Generate a speech mask using WebRTC VAD."""
    logger.debug(f"Generating speech mask for audio with {len(audio)} samples")
    vad = webrtcvad.Vad(2)
    frame_length = int(sr * frame_duration_ms / 1000)
    padded_audio = np.pad(
        audio, (0, frame_length - len(audio) % frame_length), mode="constant"
    )
    frames = np.reshape(padded_audio, (-1, frame_length))
    speech_mask = np.zeros(len(audio), dtype=bool)

    for i, frame in enumerate(frames):
        byte_data = (frame * 32768).astype(np.int16).tobytes()
        is_speech = vad.is_speech(byte_data, sample_rate=sr)
        if is_speech:
            start = i * frame_length
            end = min((i + 1) * frame_length, len(audio))
            speech_mask[start:end] = True

    speech_percentage = (np.sum(speech_mask) / len(speech_mask)) * 100
    logger.debug(f"Speech detected in {speech_percentage:.2f}% of the audio")
    return speech_mask


@performance_log
def isolate_speech_focused_batch(audio_segment_path: str, output_path: str) -> str:
    """Isolate speech from a single audio segment by reducing noise."""
    logger.info(f"Starting speech isolation for audio segment: {audio_segment_path}")
    try:
        y, sr = sf.read(audio_segment_path)
        logger.debug(f"Audio segment loaded: {len(y)} samples at {sr}Hz")

        if y.ndim > 1:
            y = np.mean(y, axis=1)
            logger.debug("Converted stereo to mono for segment")

        speech_mask = get_speech_mask(y, sr)
        noise_profile = y[~speech_mask]

        if len(noise_profile) < 1:
            logger.warning(
                "No noise profile could be generated for segment, falling back to full segment audio"
            )
            noise_profile = y

        logger.debug("Starting noise reduction for segment...")
        reduced_audio = nr.reduce_noise(
            y=y,
            sr=sr,
            y_noise=noise_profile,
            stationary=False,
            prop_decrease=0.8,
            use_tqdm=False,  # Set to False for non-interactive batch processing
        )

        sf.write(output_path, reduced_audio, sr)
        logger.debug(
            f"Speech isolation completed for segment. Output saved to: {output_path}"
        )
        return output_path
    except Exception as e:
        logger.error(f"Failed to isolate speech for segment: {str(e)}", exc_info=True)
        return None


@performance_log
def prepare_audio(video_path: str, raw_audio_path: str, cleaned_audio_path: str):
    """Prepare audio by extracting and cleaning it from a video.
    This function is now primarily for initial extraction.
    Speech isolation will be handled segment-wise.
    """
    logger.info(f"Starting audio preparation for video: {video_path}")
    try:
        extract_audio_from_video(video_path, raw_audio_path)
        # We no longer call isolate_speech_focused here, as it will be done per segment.
        # For now, just copy the raw audio to cleaned_audio_path to ensure the file exists
        # for subsequent segment cutting. The actual cleaning happens in isolate_speech_focused_batch.
        shutil.copy(raw_audio_path, cleaned_audio_path)
        logger.info(f"Raw audio copied to cleaned_audio_path: {cleaned_audio_path}")
    except Exception as e:
        logger.error(f"Audio preparation failed: {str(e)}", exc_info=True)
        raise
