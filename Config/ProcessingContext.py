import os


class ProcessingContext:
    """Context for video processing."""

    def __init__(self, task_id: str, video_path: str, output_folder: str):
        self.task_id = task_id
        self.video_path = video_path
        self.output_folder = output_folder
        self.raw_audio_path = os.path.join(output_folder, "raw_audio.wav")
        self.cleaned_audio_path = os.path.join(
            output_folder, "cleaned_speech.wav")