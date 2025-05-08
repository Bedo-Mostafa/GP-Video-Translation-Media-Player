import shutil
import subprocess

import noisereduce as nr
import numpy as np
import soundfile as sf
import webrtcvad

from ..utils.aspect import performance_log


@performance_log
def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())


@performance_log
def extract_audio_from_video(video_path: str, output_path: str) -> str:
    """Extract audio from a video file using ffmpeg."""
    print("Extracting audio from video...")
    extract_cmd = [
        "ffmpeg", "-y", "-i", video_path, "-vn",
        "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path
    ]
    try:
        result = subprocess.run(extract_cmd, check=True,
                                capture_output=True, text=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] FFmpeg failed: {e.stderr}")
        raise
    except FileNotFoundError:
        print(
            "[ERROR] FFmpeg not found. Please ensure FFmpeg is installed and added to your PATH.")
        raise


@performance_log
def get_speech_mask(audio: np.ndarray, sr: int, frame_duration_ms: int = 30) -> np.ndarray:
    """Generate a speech mask using WebRTC VAD."""
    vad = webrtcvad.Vad(2)
    frame_length = int(sr * frame_duration_ms / 1000)
    padded_audio = np.pad(
        audio, (0, frame_length - len(audio) % frame_length), mode='constant')
    frames = np.reshape(padded_audio, (-1, frame_length))
    speech_mask = np.zeros(len(audio), dtype=bool)
    for i, frame in enumerate(frames):
        byte_data = (frame * 32768).astype(np.int16).tobytes()
        is_speech = vad.is_speech(byte_data, sample_rate=sr)
        if is_speech:
            start = i * frame_length
            end = min((i + 1) * frame_length, len(audio))
            speech_mask[start:end] = True
    return speech_mask


@performance_log
def isolate_speech_focused(audio_path: str, output_speech_path: str) -> str:
    """Isolate speech from audio by reducing noise."""
    try:
        y, sr = sf.read(audio_path)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        speech_mask = get_speech_mask(y, sr)
        noise_profile = y[~speech_mask]
        if len(noise_profile) < 1:
            print(
                "[WARN] No noise profile could be generated, falling back to full audio")
            noise_profile = y
        reduced_audio = nr.reduce_noise(
            y=y, sr=sr, y_noise=noise_profile, stationary=False, prop_decrease=0.8, use_tqdm=True
        )
        sf.write(output_speech_path, reduced_audio, sr)
        print(f"[SUCCESS] Isolated speech saved to: {output_speech_path}")
        return output_speech_path
    except Exception as e:
        print(f"[ERROR] Failed to isolate speech: {e}")
        return None


@performance_log
def prepare_audio(video_path: str, raw_audio_path: str, cleaned_audio_path: str):
    """Prepare audio by extracting and cleaning it from a video."""
    extract_audio_from_video(video_path, raw_audio_path)
    result = isolate_speech_focused(raw_audio_path, cleaned_audio_path)
    if not result:
        print("[WARNING] Using original audio instead.")
        shutil.copy(raw_audio_path, cleaned_audio_path)
