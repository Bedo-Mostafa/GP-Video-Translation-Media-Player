import subprocess
from typing import List, Tuple

import librosa
import numpy as np

from ..utils.aspect import performance_log
from .processing import get_video_duration


@performance_log
def detect_silent_points(
    audio_path: str,
    min_silence_duration: float = 0.7,
    silence_threshold_db: float = -35,
) -> List[float]:
    """Detect silent points in audio for segmentation."""
    audio, sr = librosa.load(audio_path, sr=None)
    frame_length = 2048
    hop_length = 512
    rms = librosa.feature.rms(
        y=audio, frame_length=frame_length, hop_length=hop_length
    )[0]
    db = librosa.amplitude_to_db(rms, ref=np.max)
    silent_regions = []
    silent_start = None
    for i, value in enumerate(db):
        current_time = i * hop_length / sr
        if value < silence_threshold_db:
            if silent_start is None:
                silent_start = current_time
        else:
            if silent_start is not None:
                silent_duration = current_time - silent_start
                if silent_duration >= min_silence_duration:
                    midpoint = silent_start + silent_duration / 2
                    silent_regions.append(midpoint)
                silent_start = None
    return silent_regions


@performance_log
def segment_audio(
    audio_path: str,
    video_path: str,
    min_silence_duration: float,
    silence_threshold: float,
) -> List[float]:
    """Segment audio based on silent points or time-based intervals."""
    print("Detecting silent points for segmentation...")
    silent_points = detect_silent_points(
        audio_path, min_silence_duration, silence_threshold
    )
    silent_points = sorted(set(round(p, 2) for p in silent_points))
    video_duration = get_video_duration(video_path)
    if len(silent_points) < 3:
        print("Few silent points detected. Creating time-based segments...")
        segment_length = 30
        silent_points = [
            i * segment_length for i in range(1, int(video_duration / segment_length))
        ]
    silent_points = [p for p in silent_points if p < video_duration - 1]
    return silent_points


@performance_log
def create_segment_jobs(
    silent_points: List[float], video_duration: float
) -> List[Tuple[float, float, int]]:
    """Create jobs for segmenting audio based on silent points."""
    points = [0.0] + silent_points + [video_duration]
    jobs = []
    for idx in range(len(points) - 1):
        start = points[idx]
        end = points[idx + 1]
        if start < end:
            jobs.append((start, end, idx))
    return jobs


@performance_log
def cut_audio_segment(
    input_audio: str, output_path: str, start_time: float, end_time: float
) -> str:
    """Cut an audio segment using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_time),
        "-i",
        input_audio,
        "-loglevel",
        "error",
    ]
    if end_time is not None:
        duration = float(end_time) - float(start_time)
        cmd.extend(["-t", str(duration)])
    cmd.append(output_path)
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path
