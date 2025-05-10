from ..audio.processing import get_video_duration


class ProcessingContext:
    """Context for processing a transcription task."""

    def __init__(self, task_id: str, video_path: str, output_folder: str):
        self.task_id = task_id
        self.video_path = video_path
        self.output_folder = output_folder
        self.raw_audio_path = f"{output_folder}/raw_audio.wav"
        self.cleaned_audio_path = f"{output_folder}/cleaned_audio.wav"

    def get_video_duration(self) -> float:
        """Get the duration of the video."""
        return get_video_duration(self.video_path)
