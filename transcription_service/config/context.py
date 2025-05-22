from ..audio.audio_processing import get_video_duration
import numpy as np  # Added for type hinting
from typing import Optional  # Added for type hinting


class ProcessingContext:
    """Context for processing a transcription task."""

    def __init__(self, task_id: str, video_path: str, output_folder: str):
        self.task_id: str = task_id
        self.video_path: str = video_path
        self.output_folder: str = output_folder

        # Original path attributes
        self.raw_audio_path: str = f"{output_folder}/raw_audio.wav"
        self.cleaned_audio_path: str = f"{output_folder}/cleaned_audio.wav"
        # These paths might be used for initial ffmpeg output before loading to RAM,
        # or by the batch processing path if it's not fully using in-memory data.

        # New attributes for in-memory audio processing
        self.audio_data_np: Optional[np.ndarray] = None
        self.sample_rate: Optional[int] = None

    def get_video_duration(self) -> float:
        """Get the duration of the video."""
        return get_video_duration(self.video_path)
