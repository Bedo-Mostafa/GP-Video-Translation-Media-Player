class TranscriptionConfig:
    """Configuration for transcription tasks."""

    def __init__(
        self,
        model_name: str,
        max_workers: int,
        min_silence_duration: float,
        silence_threshold: float,
    ):
        self.model_name = model_name
        self.max_workers = max_workers
        self.min_silence_duration = min_silence_duration
        self.silence_threshold = silence_threshold
