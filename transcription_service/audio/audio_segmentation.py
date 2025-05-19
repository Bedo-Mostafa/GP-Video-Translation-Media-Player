import os
import librosa
import numpy as np
from typing import List, Dict
from ..utils.logging_config import get_audio_logger

logger = get_audio_logger()

def detect_silent_points(audio_path: str) -> List[float]:
    """Detect silent points in audio for segmentation.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        List of timestamps where silence occurs
    """
    logger.info(f"Detecting silent points in audio: {audio_path}")
    
    try:
        # Load audio file
        logger.debug("Loading audio file...")
        y, sr = librosa.load(audio_path, sr=None)
        
        # Calculate energy
        logger.debug("Calculating audio energy...")
        energy = librosa.feature.rms(y=y)[0]
        
        # Find silent points
        logger.debug("Finding silent points...")
        threshold = np.mean(energy) * 0.5
        silent_frames = np.where(energy < threshold)[0]
        
        # Convert frame indices to timestamps
        silent_points = librosa.frames_to_time(silent_frames, sr=sr)
        
        logger.info(f"Found {len(silent_points)} silent points")
        return silent_points.tolist()
        
    except Exception as e:
        error_msg = f"Error detecting silent points: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise

def segment_audio(audio_path: str, video_path: str) -> List[Dict]:
    """Segment audio based on silent points or create time-based segments.
    
    Args:
        audio_path: Path to audio file
        video_path: Path to video file for duration reference
        
    Returns:
        List of segment dictionaries containing timing and path information
    """
    logger.info(f"Segmenting audio: {audio_path}")
    
    try:
        # Get video duration
        from .audio_processing import get_video_duration
        video_duration = get_video_duration(video_path)
        logger.debug(f"Video duration: {video_duration} seconds")
        
        # Detect silent points
        silent_points = detect_silent_points(audio_path)
        
        # Create segments
        if len(silent_points) > 0:
            logger.info("Creating segments based on silent points")
            segments = create_segment_jobs(silent_points, video_duration)
        else:
            logger.info("No silent points detected, creating time-based segments")
            segments = create_time_based_segments(video_duration)
        
        logger.info(f"Created {len(segments)} segments")
        return segments
        
    except Exception as e:
        error_msg = f"Error segmenting audio: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise

def create_segment_jobs(silent_points: List[float], video_duration: float) -> List[Dict]:
    """Create jobs for segmenting audio based on detected silent points.
    
    Args:
        silent_points: List of timestamps where silence occurs
        video_duration: Total duration of the video
        
    Returns:
        List of segment dictionaries
    """
    logger.debug("Creating segment jobs from silent points")
    
    segments = []
    start_time = 0.0
    
    for i, point in enumerate(silent_points):
        if point - start_time >= 5.0:  # Minimum segment duration
            segment = {
                "id": f"segment_{i}",
                "start_time": start_time,
                "end_time": point,
                "audio_path": None  # Will be set when segment is cut
            }
            segments.append(segment)
            start_time = point
    
    # Add final segment if needed
    if video_duration - start_time >= 5.0:
        segments.append({
            "id": f"segment_{len(segments)}",
            "start_time": start_time,
            "end_time": video_duration,
            "audio_path": None
        })
    
    logger.debug(f"Created {len(segments)} segment jobs")
    return segments

def create_time_based_segments(video_duration: float) -> List[Dict]:
    """Create time-based segments when no silent points are detected.
    
    Args:
        video_duration: Total duration of the video
        
    Returns:
        List of segment dictionaries
    """
    logger.debug("Creating time-based segments")
    
    segment_duration = 30.0  # 30 seconds per segment
    segments = []
    
    for i in range(0, int(video_duration), int(segment_duration)):
        end_time = min(i + segment_duration, video_duration)
        segments.append({
            "id": f"segment_{i//int(segment_duration)}",
            "start_time": float(i),
            "end_time": end_time,
            "audio_path": None
        })
    
    logger.debug(f"Created {len(segments)} time-based segments")
    return segments

def cut_audio_segment(input_audio: str, output_path: str, start_time: float, end_time: float) -> None:
    """Cut an audio segment using ffmpeg.
    
    Args:
        input_audio: Path to input audio file
        output_path: Path to save the cut segment
        start_time: Start time in seconds
        end_time: End time in seconds
    """
    logger.debug(f"Cutting audio segment from {start_time} to {end_time}")
    
    try:
        import subprocess
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i", input_audio,
            "-ss", str(start_time),
            "-to", str(end_time),
            "-c:a", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_path
        ]
        
        # Execute ffmpeg command
        logger.debug(f"Executing ffmpeg command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True)
        
        logger.debug(f"Audio segment saved to: {output_path}")
        
    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg error: {e.stderr.decode()}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Error cutting audio segment: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise 