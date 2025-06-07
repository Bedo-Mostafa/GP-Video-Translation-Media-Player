import os
from hashlib import sha256
from services.audio.audio_processing import get_video_metadata
from numpy import ndarray
from typing import Optional


class ProcessingContext:
    """Context for processing a transcription task."""

    def __init__(
        self,
        task_id: str,
        video_path: str,
        src_lang: str,
        tgt_lang: str,
        output_folder: str,
    ):
        self.task_id: str = task_id
        self.video_path: str = video_path
        self.src_lang: str = src_lang
        self.tgt_lang: str = tgt_lang
        self.output_folder: str = output_folder
        self.video_metadata: dict = get_video_metadata(self.video_path)

        # Original path attributes
        self.raw_audio_path: str = f"{output_folder}/raw_audio.wav"
        self.cleaned_audio_path: str = f"{output_folder}/cleaned_audio.wav"

        # New attributes for in-memory audio processing
        self.audio_data_np: Optional[ndarray] = None
        self.sample_rate: Optional[int] = None

    def get_video_duration(self) -> float:
        """Get the duration of the video."""
        return self.video_metadata["duration"]

    def get_video_hash(self) -> str:
        """Get the hashed name of the video."""
        metadata = self.video_metadata
        raw_data = f"{metadata['duration']}-{metadata['width']}-{metadata['height']}-{metadata['bitrate']}"
        short_hash = sha256(raw_data.encode()).hexdigest()[:16]
        return short_hash

    def get_srt_file(self, lang, is_lock) -> str:
        video_hash = self.get_video_hash()
        return os.path.join(
            "transcriptions/", f"{video_hash}.{lang}.srt{'.lock' if is_lock else ''}"
        )
