from transcription_service.api.VideoProcessor import DEFAULT_OUTPUT_QUEUE_SIZE, logger
from transcription_service.api.constants import STOP_SIGNAL


import threading
from queue import Full as QueueFull, Queue
from typing import Tuple

DEFAULT_OUTPUT_QUEUE_SIZE = 100  # Final client output queue size (used by TaskManager)


class TaskManager:
    # Manages the final client_output_queue and cancellation events
    def __init__(self):
        self.segment_queues = {}  # This is now the client_output_queue per task
        self.cancel_events = {}
        self.cancel_events_lock = threading.Lock()

    def register_task(self, task_id: str) -> Tuple[Queue, threading.Event]:
        with self.cancel_events_lock:
            if task_id not in self.cancel_events:
                self.cancel_events[task_id] = threading.Event()
            if task_id not in self.segment_queues:
                self.segment_queues[task_id] = Queue(maxsize=DEFAULT_OUTPUT_QUEUE_SIZE)
        return self.segment_queues[task_id], self.cancel_events[task_id]

    def cancel_task(self, task_id: str) -> None:
        with self.cancel_events_lock:
            if task_id in self.cancel_events:
                self.cancel_events[task_id].set()
                logger.info(f"Task {task_id} cancellation requested")

    def is_cancelled(self, task_id: str) -> bool:
        return self.cancel_events.get(task_id, threading.Event()).is_set()

    def cleanup_task(self, task_id: str) -> None:
        with self.cancel_events_lock:
            if task_id in self.cancel_events:
                del self.cancel_events[task_id]
            if task_id in self.segment_queues:
                try:
                    self.segment_queues[task_id].put_nowait(STOP_SIGNAL)
                except QueueFull:
                    logger.warning(
                        f"Output queue for task {task_id} was full during cleanup_task for STOP_SIGNAL."
                    )
                except Exception:
                    pass
                del self.segment_queues[task_id]
