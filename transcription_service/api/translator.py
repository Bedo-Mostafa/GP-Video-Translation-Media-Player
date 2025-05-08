from queue import Queue
import threading

from transcription_service.api.constants import STOP_SIGNAL

from ..config.context import ProcessingContext
from ..utils.aspect import performance_log


class Translator:
    """Handles translation of transcribed segments."""

    def __init__(self):
        self.nmt_model = None
        self.tokenizer = None

    @performance_log
    def translate_segment(self, segment: dict) -> dict:
        """Translate segment text using MarianMT model."""
        try:
            translated = self.nmt_model.generate(
                **self.tokenizer(segment["text"], return_tensors="pt", padding=True, truncation=True).to(self.nmt_model.device)
            )
            return {**segment, "text": self.tokenizer.decode(translated[0], skip_special_tokens=True)}
        except Exception:
            return {**segment, "text": "[Translation Error]"}

    @performance_log
    def translation_worker(self, translation_queue: Queue, context: ProcessingContext, language: bool, segment_queues: dict, cancel_events: dict):
        """Process segments for translation and queue results."""
        while True:
            if cancel_events.get(context.task_id, threading.Event()).is_set():
                print(
                    f"Task {context.task_id} canceled. Stopping translation worker.")
                break
            segment = translation_queue.get()
            if segment is STOP_SIGNAL:
                break
            if language:
                segment = self.translate_segment(segment)
            if cancel_events.get(context.task_id, threading.Event()).is_set():
                print(
                    f"Task {context.task_id} canceled. Stopping translation worker.")
                break
            segment_queues[context.task_id].put({
                "segment_index": segment["index"],
                "start_time": segment["start"],
                "end_time": segment["end"],
                "text": segment["text"]
            })
            translation_queue.task_done()
