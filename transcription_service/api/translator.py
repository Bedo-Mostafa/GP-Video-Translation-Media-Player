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
                **self.tokenizer(
                    segment["text"], return_tensors="pt", padding=True, truncation=True
                ).to(self.nmt_model.device)
            )
            return {
                **segment,
                "text": self.tokenizer.decode(translated[0], skip_special_tokens=True),
            }
        except Exception:
            return {**segment, "text": "[Translation Error]"}

    @performance_log
    def translation_worker(
        self,
        translation_queue: Queue,
        context: ProcessingContext,
        language: bool,
        segment_queues: dict,
        cancel_events: dict,
    ):
        """Process segments for translation and queue results."""
        try:
            while True:
                if cancel_events.get(context.task_id, threading.Event()).is_set():
                    print(
                        f"Task {context.task_id} canceled. Stopping translation worker."
                    )
                    break

                try:
                    # Use a timeout to check for cancellation periodically
                    segment = translation_queue.get(timeout=0.5)
                except:
                    # If the queue is empty, check for cancellation again
                    continue

                if segment is STOP_SIGNAL:
                    break

                # Check for cancellation before processing
                if cancel_events.get(context.task_id, threading.Event()).is_set():
                    print(
                        f"Task {context.task_id} canceled. Stopping translation worker."
                    )
                    break

                # Process the segment
                if language:
                    segment = self.translate_segment(segment)

                # Check for cancellation after processing
                if cancel_events.get(context.task_id, threading.Event()).is_set():
                    print(
                        f"Task {context.task_id} canceled. Stopping translation worker."
                    )
                    break

                # Queue the segment for streaming
                if context.task_id in segment_queues:
                    segment_queues[context.task_id].put(
                        {
                            "segment_index": segment["index"],
                            "start_time": segment["start"],
                            "end_time": segment["end"],
                            "text": segment["text"],
                        }
                    )

                translation_queue.task_done()
        except Exception as e:
            print(f"Error in translation worker: {e}")
        finally:
            print(f"Translation worker for task {context.task_id} exited")
