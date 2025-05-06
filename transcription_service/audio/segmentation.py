import subprocess
import time
from typing import List, Tuple

import librosa
import numpy as np

from ..utils.logger import Logger
from .processing import get_video_duration

def detect_silent_points(audio_path: str, logger: Logger, min_silence_duration: float = 0.7, silence_threshold_db: float = -35) -> List[float]:
    """Detect silent points in audio for segmentation."""
    start_time = time.time()
    audio, sr = librosa.load(audio_path, sr=None)
    frame_length = 2048
    hop_length = 512
    rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
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
    elapsed_time = time.time() - start_time
    logger.log_step(
        "Detect Silent Points", elapsed_time,
        f"Audio: {audio_path}, Silent Regions Found: {len(silent_regions)}"
    )
    return silent_regions

def segment_audio(audio_path: str, video_path: str, min_silence_duration: float, silence_threshold: float, logger: Logger) -> List[float]:
    """Segment audio based on silent points or time-based intervals."""
    print("Detecting silent points for segmentation...")
    start_time = time.time()
    silent_points = detect_silent_points(audio_path, logger, min_silence_duration, silence_threshold)
    silent_points = sorted(set(round(p, 2) for p in silent_points))
    video_duration = get_video_duration(video_path)
    if len(silent_points) < 3:
        print("Few silent points detected. Creating time-based segments...")
        segment_length = 30
        silent_points = [i * segment_length for i in range(1, int(video_duration / segment_length))]
    silent_points = [p for p in silent_points if p < video_duration - 1]
    elapsed_time = time.time() - start_time
    logger.log_step(
        "Segment Audio", elapsed_time,
        f"Audio: {audio_path}, Video: {video_path}, Segments: {len(silent_points)}"
    )
    return silent_points

def create_segment_jobs(silent_points: List[float], video_duration: float, logger: Logger) -> List[Tuple[float, float, int]]:
    """Create jobs for segmenting audio based on silent points."""
    start_time = time.time()
    points = [0.0] + silent_points + [video_duration]
    jobs = []
    for idx in range(len(points) - 1):
        start = points[idx]
        end = points[idx + 1]
        if start < end:
            jobs.append((start, end, idx))
    elapsed_time = time.time() - start_time
    logger.log_step(
        "Create Segment Jobs", elapsed_time,
        f"Total Jobs: {len(jobs)}, Video Duration: {video_duration:.2f}s"
    )
    return jobs

def cut_audio_segment(input_audio: str, output_path: str, start_time: float, end_time: float, logger: Logger) -> str:
    """Cut an audio segment using ffmpeg."""
    start_time_segment = time.time()
    cmd = ["ffmpeg", "-y", "-ss", str(start_time), "-i", input_audio, "-loglevel", "error"]
    if end_time is not None:
        duration = float(end_time) - float(start_time)
        cmd.extend(["-t", str(duration)])
    cmd.append(output_path)
    subprocess.run(cmd, check=True, capture_output=True)
    elapsed_time = time.time() - start_time_segment
    logger.log_step(
        "Cut Audio Segment", elapsed_time,
        f"Input: {input_audio}, Output: {output_path}, Start: {start_time:.2f}s, End: {end_time if end_time is not None else 'N/A'}"
    )
    return output_path