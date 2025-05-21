import os
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from queue import Queue
from typing import List, Tuple, Dict, Optional
import soundfile as sf

import librosa
import numpy as np

from .constants import STOP_SIGNAL
from ..audio.audio_processing import (
    get_video_duration,
    prepare_audio,
    isolate_speech_focused_batch,
)  # Import the new batch isolation function
from ..audio.audio_segmentation_progressive import (
    segment_audio_progressive,
    cut_audio_segment,
)
from ..config.context import ProcessingContext
from ..config.transcription_config import TranscriptionConfig
from ..models.model_loader import load_whisper_model
from ..models.model_config import ModelConfig, default_config
from ..utils.aspect import performance_log
from ..transcription.transcriber import transcribe_segment
from ..transcription.translator import Translator
from ..utils.logging_config import get_processor_logger

logger = get_processor_logger()


class VideoProcessor:
    """Handles video processing, audio segmentation, and transcription."""

    def __init__(self):
        self.segment_queues = {}
        self.model_cache = {}
        self.cancel_events = {}
        self.cancel_events_lock = threading.Lock()
        self.whisper_model = None
        self.model_config = default_config
        logger.info("TranscriptionProcessor initialized")

    @performance_log
    def prepare_audio_files(self, context: ProcessingContext):
        """Prepare audio files by extracting and cleaning audio from video."""
        # This now only extracts the raw audio. Batch isolation happens per segment.
        prepare_audio(
            context.video_path, context.raw_audio_path, context.cleaned_audio_path
        )

    @performance_log
    def load_transcription_model(self, config: ModelConfig):
        """Load or get cached Whisper model.

        Args:
            config: ModelConfig instance with model settings
        """
        if self.whisper_model is None or self.model_config != config:
            logger.info(f"Loading transcription model with config: {config}")
            self.whisper_model = load_whisper_model(config)
            self.model_config = config
            logger.info("Transcription model loaded successfully")
        else:
            logger.debug("Using cached transcription model")

    @performance_log
    def process_segment(
        self,
        job: Tuple[float, float, int],
        model,
        context: ProcessingContext,
        translation_queue: Queue,
    ):
        """Process a single audio segment for transcription, including speech isolation."""
        start_time, end_time, segment_idx = job
        temp_raw_audio_segment_file = os.path.join(
            context.output_folder, f"segment_{segment_idx}_raw_audio.wav"
        )
        temp_cleaned_audio_segment_file = os.path.join(
            context.output_folder, f"segment_{segment_idx}_cleaned_audio.wav"
        )

        try:
            if self.cancel_events.get(context.task_id, threading.Event()).is_set():
                print(f"Task {context.task_id} canceled. Stopping segment processing.")
                return

            # Cut the raw audio segment
            cut_audio_segment(
                context.cleaned_audio_path,
                temp_raw_audio_segment_file,
                start_time,
                end_time,
            )

            # Isolate speech for the current segment
            isolated_audio_path = isolate_speech_focused_batch(
                temp_raw_audio_segment_file, temp_cleaned_audio_segment_file
            )

            if not isolated_audio_path:
                logger.warning(
                    f"Speech isolation failed for segment {segment_idx}. Skipping transcription."
                )
                return

            # Transcribe the isolated speech segment
            adjusted_segments = transcribe_segment(
                model, isolated_audio_path, start_time, end_time
            )

            for segment in adjusted_segments:
                if self.cancel_events.get(context.task_id, threading.Event()).is_set():
                    print(
                        f"Task {context.task_id} canceled. Stopping segment processing."
                    )
                    return
                segment["index"] = segment_idx
                translation_queue.put(segment)
        except Exception as e:
            print(f"Error processing segment {segment_idx}: {str(e)}")
        finally:
            # Clean up temporary audio files for the segment
            if os.path.exists(temp_raw_audio_segment_file):
                os.remove(temp_raw_audio_segment_file)
            if os.path.exists(temp_cleaned_audio_segment_file):
                os.remove(temp_cleaned_audio_segment_file)

    @performance_log
    def process_segments_worker(
        self,
        context: ProcessingContext,
        segment_queue: Queue,
        translation_queue: Queue,
        pool: ThreadPoolExecutor,
        first_segment_event: threading.Event,  # New parameter
    ):
        """Process segments as they are detected and added to the queue.

        Args:
            context: ProcessingContext with task information
            segment_queue: Queue to receive segments from segmentation process
            translation_queue: Queue to send transcribed segments to translation
            pool: ThreadPoolExecutor for transcription tasks
            first_segment_event: Event to wait for the first segment to be queued
        """
        # Wait for the first segment to be queued
        logger.debug(f"Waiting for first segment for task {context.task_id}")
        first_segment_event.wait()
        logger.debug(
            f"First segment received for task {context.task_id}, starting processing"
        )

        futures = []

        while True:
            # Check if task was cancelled
            if self.cancel_events.get(context.task_id, threading.Event()).is_set():
                print(f"Task {context.task_id} canceled in segment worker. Stopping.")
                break

            try:
                # Get next segment job from queue
                job = segment_queue.get(timeout=0.5)

                # None marks the end of segmentation
                if job is None:
                    print(f"Finished receiving segments for task {context.task_id}")
                    break

                # Submit job for processing
                futures.append(
                    pool.submit(
                        self.process_segment,
                        job,
                        self.whisper_model,
                        context,
                        translation_queue,
                    )
                )

            except Exception as e:
                # Handle queue timeout or other errors
                if "Empty" not in str(e):  # Only log non-timeout errors
                    print(f"Error in segment worker: {str(e)}")

        # Wait for remaining jobs to complete
        try:
            if futures:
                wait(futures)
        except Exception as e:
            print(f"Error waiting for segment futures: {str(e)}")

        # Signal that all transcriptions are complete
        translation_queue.put(STOP_SIGNAL)
        print(f"Segment worker for task {context.task_id} completed")

    @performance_log
    def process_video_with_streaming(
        self,
        context: ProcessingContext,
        config: TranscriptionConfig,
        language: bool,
        translator: Translator,
    ):
        """Process video for transcription and streaming results using progressive segmentation."""
        try:
            # Create a cancellation event for this task
            cancel_event = threading.Event()
            with self.cancel_events_lock:
                self.cancel_events[context.task_id] = cancel_event

            # Create a queue for this task if it doesn't exist
            if context.task_id not in self.segment_queues:
                self.segment_queues[context.task_id] = Queue()

            # Prepare the audio files (extracts raw audio)
            self.prepare_audio_files(context)

            # Check if cancellation was requested during audio preparation
            if cancel_event.is_set():
                print(f"Task {context.task_id} cancelled during audio preparation")
                if context.task_id in self.segment_queues:
                    self.segment_queues[context.task_id].put(
                        {"status": "cancelled", "message": "Task cancelled"}
                    )
                    self.segment_queues[context.task_id].put(STOP_SIGNAL)
                return

            # Load the transcription model
            self.load_transcription_model(self.model_config)

            # Check if cancellation was requested during model loading
            if cancel_event.is_set():
                print(f"Task {context.task_id} cancelled during model loading")
                if context.task_id in self.segment_queues:
                    self.segment_queues[context.task_id].put(
                        {"status": "cancelled", "message": "Task cancelled"}
                    )
                    self.segment_queues[context.task_id].put(STOP_SIGNAL)
                return

            # Create queues for segments and translation
            segment_queue = Queue()
            translation_queue = Queue()

            # Create event to signal when the first segment is queued
            first_segment_event = threading.Event()

            # Start segmentation in a separate thread to identify segments progressively
            segmentation_thread = threading.Thread(
                target=segment_audio_progressive,
                args=(
                    context.cleaned_audio_path,  # This is now the raw audio path after initial extraction
                    context.video_path,
                    segment_queue,
                    cancel_event,
                    first_segment_event,  # Pass the first_segment_event
                ),
                daemon=True,
            )
            segmentation_thread.start()

            # Start segment worker before segmentation to process segments as soon as they are queued
            with ThreadPoolExecutor(max_workers=config.max_workers) as pool:
                segment_worker = threading.Thread(
                    target=self.process_segments_worker,
                    args=(
                        context,
                        segment_queue,
                        translation_queue,
                        pool,
                        first_segment_event,
                    ),
                    daemon=True,
                )
                segment_worker.start()

                # Start translation worker
                translator_thread = threading.Thread(
                    target=translator.translation_worker,
                    args=(
                        translation_queue,
                        context,
                        language,
                        self.segment_queues,
                        self.cancel_events,
                    ),
                    daemon=True,
                )
                translator_thread.start()

                # Wait for segmentation and processing to complete
                segmentation_thread.join()
                segment_worker.join()

            # Wait for translator to complete
            translator_thread.join(timeout=5)

            # Ensure we send a final signal to the client
            if context.task_id in self.segment_queues:
                if cancel_event.is_set():
                    self.segment_queues[context.task_id].put(
                        {"status": "cancelled", "message": "Task cancelled"}
                    )
                self.segment_queues[context.task_id].put(STOP_SIGNAL)

        except Exception as e:
            print(f"Error in video processing: {e}")
            if context.task_id in self.segment_queues:
                self.segment_queues[context.task_id].put(STOP_SIGNAL)
        finally:
            # Clean up resources
            try:
                if os.path.exists(context.output_folder):
                    shutil.rmtree(context.output_folder)
            except Exception as e:
                print(f"Error cleaning up output folder: {e}")

    def process_video(self, video_path: str, output_folder: str) -> Dict:
        """Process video file for transcription.

        Args:
            video_path: Path to input video file
            output_folder: Path to output folder for results

        Returns:
            Dict containing processing results
        """
        logger.info(f"Starting video processing: {video_path}")

        try:
            # Create temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.debug(f"Created temporary directory: {temp_dir}")

                # Prepare audio files
                raw_audio_path = os.path.join(temp_dir, "raw_audio.wav")
                cleaned_audio_path = os.path.join(
                    temp_dir, "cleaned_audio.wav"
                )  # This will now hold the raw audio initially

                logger.info("Preparing audio files...")
                prepare_audio(
                    video_path, raw_audio_path, cleaned_audio_path
                )  # Only extracts raw audio now

                # Segment audio (this will now segment the raw audio)
                logger.info("Segmenting audio...")
                # The process_video method is not designed for streaming,
                # so we'll keep the original segmentation logic for this non-streaming path.
                # However, the _process_segment will now handle batch isolation.
                from ..audio.audio_segmentation_progressive import (
                    detect_silent_points_progressive,
                    create_time_based_segments,
                    create_segment_jobs,
                )

                y, sr = sf.read(
                    cleaned_audio_path
                )  # Read the initially extracted raw audio
                energy = librosa.feature.rms(y=y)[0]
                threshold = np.mean(energy) * 0.5
                silent_frames = np.where(energy < threshold)[0]
                silent_points = librosa.frames_to_time(silent_frames, sr=sr)

                video_duration = get_video_duration(video_path)

                if silent_points.size > 0:
                    segments = create_segment_jobs(silent_points, video_duration)
                else:
                    segments = create_time_based_segments(video_duration)

                logger.info(f"Created {len(segments)} audio segments")

                # Process each segment
                results = []
                for i, segment in enumerate(segments, 1):
                    logger.info(f"Processing segment {i}/{len(segments)}")
                    # For the non-streaming path, we need to cut the segment and then isolate speech
                    segment_raw_audio_path = os.path.join(
                        temp_dir, f"segment_{i}_raw_audio.wav"
                    )
                    segment_cleaned_audio_path = os.path.join(
                        temp_dir, f"segment_{i}_cleaned_audio.wav"
                    )

                    cut_audio_segment(
                        cleaned_audio_path,
                        segment_raw_audio_path,
                        segment["start_time"],
                        segment["end_time"],
                    )
                    isolated_segment_path = isolate_speech_focused_batch(
                        segment_raw_audio_path, segment_cleaned_audio_path
                    )

                    if not isolated_segment_path:
                        logger.warning(
                            f"Speech isolation failed for segment {i}. Skipping transcription."
                        )
                        continue

                    # Update the segment's audio_path to the cleaned one for transcription
                    segment["audio_path"] = isolated_segment_path
                    segment_result = self._process_segment(segment)
                    results.append(segment_result)

                    # Clean up segment-specific temp files
                    if os.path.exists(segment_raw_audio_path):
                        os.remove(segment_raw_audio_path)
                    if os.path.exists(segment_cleaned_audio_path):
                        os.remove(segment_cleaned_audio_path)

                logger.info("Video processing completed successfully")
                return {"status": "success", "segments": results}

        except Exception as e:
            error_msg = f"Error processing video: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"status": "error", "error": error_msg}

    def _process_segment(self, segment: Dict) -> Dict:
        """Process a single audio segment.

        Args:
            segment: Dictionary containing segment information

        Returns:
            Dict containing segment processing results
        """
        try:
            logger.debug(f"Processing segment: {segment}")

            # Transcribe segment
            transcription = self.whisper_model.transcribe(
                segment["audio_path"], language="en", beam_size=5
            )

            logger.debug(f"Transcription completed for segment {segment['id']}")

            return {
                "id": segment["id"],
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "text": transcription.text,
            }

        except Exception as e:
            error_msg = f"Error processing segment {segment['id']}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"id": segment["id"], "error": error_msg}
