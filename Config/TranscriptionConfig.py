class TranscriptionConfig:
    """Configuration for transcription process."""

    def __init__(
        self,
        model_name: str = "small",
        max_workers: int = 1,
        min_silence_duration: float = 0.7,
        silence_threshold: int = -35
    ):
        self.model_name = model_name
        self.max_workers = max_workers
        self.min_silence_duration = min_silence_duration
        self.silence_threshold = silence_threshold