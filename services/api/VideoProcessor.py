import os
import shutil
import threading
import numpy as np
from queue import Empty, Queue, Full as QueueFull
from typing import Optional, Any

from services.api.Processor.AudioPreprocessor import AudioPreprocessor
from services.api.Processor.TaskManager import TaskManager

from services.api.Processor.ModelManager import ModelManager


from services.api.constants import STOP_SIGNAL
from services.config.context import ProcessingContext
from services.models.model_config import default_config
from services.utils.aspect import performance_log
from services.transcription.transcriber import transcribe_segment
from services.transcription.translator import Translator
from services.utils.logging_config import get_processor_logger

logger = get_processor_logger()


DEFAULT_TRANSCRIPTION_QUEUE_SIZE = 50


class VideoProcessor:
    def __init__(self):
        self.model_manager = ModelManager()
        self.audio_processor = AudioPreprocessor()  # Simplified preprocessor
        self.task_manager = TaskManager()
        logger.info("VideoProcessor initialized (Simplified Streaming Pipeline)")

    def _transcription_producer_worker(
        self,
        raw_audio_np: np.ndarray,
        sample_rate: int,
        whisper_model: Any,
        target_queue: Queue,
        task_id: str,
        cancel_event: threading.Event,
    ):
        segment_idx_counter = 0
        try:
            logger.info(
                f"Task {task_id} (Transcription): Audio shape: {raw_audio_np.shape}"
            )
            logger.info(
                f"Task {task_id} (Transcription): Duration: {len(raw_audio_np) / sample_rate:.2f}s"
            )
            logger.info(f"Task {task_id} (Transcription): Sample rate: {sample_rate}")

            if len(raw_audio_np) == 0:
                logger.error(f"Task {task_id} (Transcription): Audio array is empty!")
                target_queue.put(
                    {
                        "status": "error",
                        "message": "Audio array is empty",
                        "index": 0,
                    }
                )
                return

            audio_duration = len(raw_audio_np) / sample_rate

            logger.info(
                f"Task {task_id} (Transcription): Streaming transcription with `transcribe_segment`..."
            )

            for segment in transcribe_segment(
                model=whisper_model,
                audio_input=raw_audio_np,
                start_time=0.0,
                end_time=audio_duration,
            ):
                if cancel_event.is_set():
                    logger.info(
                        f"Task {task_id} (Transcription): Cancellation detected. Stopping."
                    )
                    break

                logger.info(
                    f"Task {task_id} (Transcription): Segment {segment_idx_counter}: "
                    f"start={segment['start']}, end={segment['end']}, text='{segment['text'][:50]}...'"
                )

                segment_data = {
                    "text": segment["text"],
                    "start": segment["start"],
                    "end": segment["end"],
                    "index": segment_idx_counter,
                }
                target_queue.put(segment_data)
                logger.debug(
                    f"Task {task_id} (Transcription): Produced segment {segment_idx_counter} "
                    f"({segment_data['start']:.2f}s - {segment_data['end']:.2f}s)"
                )
                segment_idx_counter += 1

        except Exception as e:
            logger.error(
                f"Task {task_id} (Transcription): Error during transcription: {e}",
                exc_info=True,
            )
            target_queue.put(
                {
                    "status": "error",
                    "message": f"Transcription process failed: {str(e)}",
                    "index": segment_idx_counter,
                }
            )

        finally:
            target_queue.put(STOP_SIGNAL)
            logger.info(
                f"Task {task_id} (Transcription): Producer finished, sent STOP_SIGNAL to target queue."
            )

    def _translation_consumer_producer_worker(
        self,
        translator_instance: Translator,
        input_queue: Queue,  # Consumes from transcription_queue
        output_queue: Queue,  # Produces to client_output_queue
        task_id: str,
        cancel_event: threading.Event,
    ):
        try:
            while True:
                if cancel_event.is_set():
                    logger.info(f"Task {task_id} (Translation): Cancellation detected.")
                    break
                try:
                    segment_to_translate = input_queue.get(timeout=0.5)
                except Empty:
                    continue

                if segment_to_translate is STOP_SIGNAL:
                    logger.info(
                        f"Task {task_id} (Translation): Received STOP_SIGNAL from transcription."
                    )
                    break

                if (
                    isinstance(segment_to_translate, dict)
                    and segment_to_translate.get("status") == "error"
                ):
                    logger.warning(
                        f"Task {task_id} (Translation): Received error signal from transcription. Propagating."
                    )
                    output_queue.put(segment_to_translate)  # Propagate error
                    # continue or break? If transcription failed, probably break.
                    break

                # segment_to_translate is {"text": "...", "start": S, "end": E, "index": I}
                # The Translator.translate_segment expects this dict structure
                translated_segment_data = translator_instance.translate_segment(
                    segment_to_translate
                )

                output_queue.put(translated_segment_data)
                logger.debug(
                    f"Task {task_id} (Translation): Produced translated segment {translated_segment_data.get('index', 'N/A')}"
                )
                input_queue.task_done()

        except Exception as e:
            logger.error(
                f"Task {task_id} (Translation): Error during translation: {e}",
                exc_info=True,
            )
            output_queue.put(
                {"status": "error", "message": "Translation process failed."}
            )
        finally:
            output_queue.put(STOP_SIGNAL)  # Ensure client queue gets stop signal
            logger.info(
                f"Task {task_id} (Translation): Consumer-Producer finished, sent STOP_SIGNAL to client output queue."
            )

    @performance_log
    def process_video_with_streaming(
        self,
        context: ProcessingContext,
        enable_translation: bool,  # Changed from 'language' to 'enable_translation' for clarity
        translator: Translator,
    ):
        task_id = context.task_id
        client_output_queue, cancel_event = self.task_manager.register_task(task_id)

        transcription_thread = None
        translator_thread = None

        try:
            self.audio_processor.load_raw_audio_into_context(context, cancel_event)

            if cancel_event.is_set():
                logger.info(f"Task {task_id}: Cancelled during raw audio loading.")
                self._handle_cancellation(task_id)  # Ensure client gets a status
                return

            if context.audio_data_np is None or context.sample_rate is None:
                logger.error(
                    f"Task {task_id}: Raw audio data could not be loaded. Aborting."
                )
                self._finalize_task(
                    task_id, error=True, message="Failed to load audio from video."
                )
                return

            whisper_model = self.model_manager.get_model(
                default_config
            )  # Load whisper model
            logger.info(f"{enable_translation}")

            if enable_translation:
                # Transcription -> Translation Queue -> Client Output Queue
                transcription_to_translation_queue = Queue(
                    maxsize=DEFAULT_TRANSCRIPTION_QUEUE_SIZE
                )

                transcription_thread = threading.Thread(
                    target=self._transcription_producer_worker,
                    args=(
                        context.audio_data_np,
                        context.sample_rate,
                        whisper_model,
                        transcription_to_translation_queue,
                        task_id,
                        cancel_event,
                    ),
                    daemon=True,
                )
                translator_thread = threading.Thread(
                    target=self._translation_consumer_producer_worker,
                    args=(
                        translator,
                        transcription_to_translation_queue,
                        client_output_queue,
                        task_id,
                        cancel_event,
                    ),
                    daemon=True,
                )
                logger.info(
                    f"Task {task_id}: Starting transcription (to translation) and translation threads."
                )
                transcription_thread.start()
                translator_thread.start()
            else:
                # Transcription -> Client Output Queue
                transcription_thread = threading.Thread(
                    target=self._transcription_producer_worker,
                    args=(
                        context.audio_data_np,
                        context.sample_rate,
                        whisper_model,
                        client_output_queue,  # Target client queue directly
                        task_id,
                        cancel_event,
                    ),
                    daemon=True,
                )
                logger.info(
                    f"Task {task_id}: Starting transcription (direct to client) thread."
                )
                transcription_thread.start()

            # Wait for threads to complete
            if transcription_thread:
                transcription_thread.join()
                logger.debug(f"Task {task_id}: Transcription producer thread joined.")
            if translator_thread:  # Only join if it was started
                translator_thread.join()
                logger.debug(f"Task {task_id}: Translation thread joined.")

            logger.debug(f"Task {task_id}: All processing threads joined. Finalizing.")

        except ValueError as ve:
            logger.error(
                f"Task {task_id}: ValueError during video processing (likely audio load): {ve}",
                exc_info=True,
            )
            self._finalize_task(task_id, error=True, message=str(ve))
        except Exception as e:
            logger.error(
                f"Task {task_id}: Unhandled error in video processing pipeline: {e}",
                exc_info=True,
            )
            self._finalize_task(
                task_id, error=True, message="An unexpected error occurred."
            )
        finally:
            if context:
                context.audio_data_np = None
            logger.debug(
                f"Task {task_id}: Cleared audio_data_np from context (if it existed)."
            )

            # Ensure output folder (for initial video save) is cleaned up
            if context and context.output_folder:
                try:
                    self._cleanup_output_folder(context.output_folder)
                except Exception as e:
                    logger.error(
                        f"Task {task_id}: Error cleaning up output folder: {e}"
                    )

            self.task_manager.cleanup_task(
                task_id
            )  # This also attempts to send STOP_SIGNAL
            logger.info(
                f"Task {task_id}: Video processing and resource cleanup finished."
            )

    def _handle_cancellation(self, task_id: str) -> None:
        if task_id in self.task_manager.segment_queues:
            try:
                # Check if queue is empty or last element isn't already a stop/cancel signal
                # This is complex to do reliably without consuming from the queue.
                # For now, just try to put. TaskManager's cleanup also tries.
                self.task_manager.segment_queues[task_id].put_nowait(
                    {"status": "cancelled", "message": "Task cancelled during setup."}
                )
                self.task_manager.segment_queues[task_id].put_nowait(STOP_SIGNAL)
            except QueueFull:
                logger.warning(
                    f"Client output queue for task {task_id} full during _handle_cancellation."
                )
            except Exception as e:
                logger.error(
                    f"Error putting cancellation message to client queue for task {task_id}: {e}"
                )

    def _finalize_task(
        self, task_id: str, error: bool = False, message: Optional[str] = None
    ) -> None:
        if task_id in self.task_manager.segment_queues:
            final_message = None
            if self.task_manager.is_cancelled(task_id):
                final_message = {
                    "status": "cancelled",
                    "message": message or "Task cancelled by user or system.",
                }
            elif error:
                final_message = {
                    "status": "error",
                    "message": message or "Processing error occurred.",
                }

            try:
                if final_message:
                    self.task_manager.segment_queues[task_id].put_nowait(final_message)

            except QueueFull:
                logger.warning(
                    f"Client output queue for task {task_id} full during _finalize_task."
                )
            except Exception as e:
                logger.error(
                    f"Error putting final status/stop signal to client queue for task {task_id}: {e}"
                )

    @staticmethod
    def _cleanup_output_folder(output_folder: str) -> None:
        # [Code from your existing VideoProcessor.py - unchanged]
        if os.path.exists(output_folder):
            try:
                shutil.rmtree(output_folder)
                logger.info(f"Successfully removed output folder: {output_folder}")
            except Exception as e:
                logger.error(f"Error removing output folder {output_folder}: {e}")
        else:
            logger.info(f"Output folder not found, no need to remove: {output_folder}")
