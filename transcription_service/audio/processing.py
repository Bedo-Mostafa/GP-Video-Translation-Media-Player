import shutil
import subprocess
import time

import librosa
import noisereduce as nr
import numpy as np
import soundfile as sf
import webrtcvad

from ..utils.logger import Logger

def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())

def extract_audio_from_video(video_path: str, output_path: str, logger: Logger) -> str:
    """Extract audio from a video file using ffmpeg."""
    print("Extracting audio from video...")
    start_time = time.time()
    extract_cmd = [
        "ffmpeg", "-y", "-i", video_path, "-vn",
        "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path
    ]
    try:
        result = subprocess.run(extract_cmd, check=True, capture_output=True, text=True)
        elapsed_time = time.time() - start_time
        logger.log_step(
            "Extract Audio from Video", elapsed_time,
            f"Video: {video_path}, Output: {output_path}"
        )
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] FFmpeg failed: {e.stderr}")
        raise
    except FileNotFoundError:
        print("[ERROR] FFmpeg not found. Please ensure FFmpeg is installed and added to your PATH.")
        raise

def get_speech_mask(audio: np.ndarray, sr: int, logger: Logger, frame_duration_ms: int = 30) -> np.ndarray:
    """Generate a speech mask using WebRTC VAD."""
    start_time = time.time()
    vad = webrtcvad.Vad(2)
    frame_length = int(sr * frame_duration_ms / 1000)
    padded_audio = np.pad(audio, (0, frame_length - len(audio) % frame_length), mode='constant')
    frames = np.reshape(padded_audio, (-1, frame_length))
    speech_mask = np.zeros(len(audio), dtype=bool)
    for i, frame in enumerate(frames):
        byte_data = (frame * 32768).astype(np.int16).tobytes()
        is_speech = vad.is_speech(byte_data, sample_rate=sr)
        if is_speech:
            start = i * frame_length
            end = min((i + 1) * frame_length, len(audio))
            speech_mask[start:end] = True
    elapsed_time = time.time() - start_time
    logger.log_step(
        "Get Speech Mask", elapsed_time,
        f"Audio Length: {len(audio)} samples, Sample Rate: {sr} Hz"
    )
    return speech_mask

def isolate_speech_focused(audio_path: str, output_speech_path: str, logger: Logger) -> str:
    """Isolate speech from audio by reducing noise."""
    start_time = time.time()
    try:
        y, sr = sf.read(audio_path)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        speech_mask = get_speech_mask(y, sr, logger)
        noise_profile = y[~speech_mask]
        if len(noise_profile) < 1:
            print("[WARN] No noise profile could be generated, falling back to full audio")
            noise_profile = y
        reduced_audio = nr.reduce_noise(
            y=y, sr=sr, y_noise=noise_profile, stationary=False, prop_decrease=0.8, use_tqdm=True
        )
        sf.write(output_speech_path, reduced_audio, sr)
        print(f"[SUCCESS] Isolated speech saved to: {output_speech_path}")
        elapsed_time = time.time() - start_time
        logger.log_step(
            "Isolate Speech Focused", elapsed_time,
            f"Input: {audio_path}, Output: {output_speech_path}"
        )
        return output_speech_path
    except Exception as e:
        print(f"[ERROR] Failed to isolate speech: {e}")
        elapsed_time = time.time() - start_time
        logger.log_step(
            "Isolate Speech Focused (Failed)", elapsed_time,
            f"Input: {audio_path}, Error: {str(e)}"
        )
        return None

def prepare_audio(video_path: str, raw_audio_path: str, cleaned_audio_path: str, logger: Logger):
    """Prepare audio by extracting and cleaning it from a video."""
    start_time = time.time()
    extract_audio_from_video(video_path, raw_audio_path, logger)
    result = isolate_speech_focused(raw_audio_path, cleaned_audio_path, logger)
    if not result:
        print("[WARNING] Using original audio instead.")
        shutil.copy(raw_audio_path, cleaned_audio_path)
    elapsed_time = time.time() - start_time
    logger.log_step(
        "Prepare Audio", elapsed_time,
        f"Video: {video_path}, Raw: {raw_audio_path}, Cleaned: {cleaned_audio_path}"
    )