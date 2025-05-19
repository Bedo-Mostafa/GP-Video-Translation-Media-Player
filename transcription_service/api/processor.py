import os
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import List, Tuple, Dict, Optional

from concurrent.futures import wait

from .constants import STOP_SIGNAL
from ..audio.audio_processing import prepare_audio
from ..audio.audio_segmentation import segment_audio, create_segment_jobs, cut_audio_segment
from ..config.context import ProcessingContext
from ..config.transcription_config import TranscriptionConfig
from ..models.model_loader import load_whisper_model
from ..models.model_config import ModelConfig, default_config
from ..utils.aspect import performance_log
from ..utils.transcription import transcribe_segment
from .translator import Translator
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
    def segment_audio_file(
        self, context: ProcessingContext, config: TranscriptionConfig
    ):
        """Segment audio based on silent points."""
        silent_points = segment_audio(
            context.cleaned_audio_path,
            context.video_path
        )
        return silent_points

    @performance_log
    def create_jobs(self, context: ProcessingContext, silent_points: List[float]):
        """Create transcription jobs from silent points."""
        jobs = create_segment_jobs(silent_points, context.get_video_duration())
        return jobs

    @performance_log
    def process_segment(
        self,
        job: Tuple[float, float, int],
        model,
        context: ProcessingContext,
        translation_queue: Queue,
    ):
        """Process a single audio segment for transcription."""
        start_time, end_time, segment_idx = job
        temp_audio_file = os.path.join(
            context.output_folder, f"segment_{segment_idx}_audio.wav"
        )
        try:
            if self.cancel_events.get(context.task_id, threading.Event()).is_set():
                print(f"Task {context.task_id} canceled. Stopping segment processing.")
                return
            cut_audio_segment(
                context.cleaned_audio_path, temp_audio_file, start_time, end_time
            )
            adjusted_segments = transcribe_segment(
                model, temp_audio_file, start_time, end_time
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
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)

    @performance_log
    def process_video_with_streaming(
        self,
        context: ProcessingContext,
        config: TranscriptionConfig,
        language: bool,
        translator: Translator,
    ):
        """Process video for transcription and streaming results."""
        try:
            # Create a cancellation event for this task
            cancel_event = threading.Event()
            with self.cancel_events_lock:
                self.cancel_events[context.task_id] = cancel_event

            # Create a queue for this task if it doesn't exist
            if context.task_id not in self.segment_queues:
                self.segment_queues[context.task_id] = Queue()

            # Prepare the audio files
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

            # Get segments from audio file
            segments = self.segment_audio_file(context, config)
            
            # Convert segments to jobs format
            jobs = [(segment["start_time"], segment["end_time"], i) 
                   for i, segment in enumerate(segments)]

            # Check if cancellation was requested during job creation
            if cancel_event.is_set():
                print(f"Task {context.task_id} cancelled during job creation")
                if context.task_id in self.segment_queues:
                    self.segment_queues[context.task_id].put(
                        {"status": "cancelled", "message": "Task cancelled"}
                    )
                    self.segment_queues[context.task_id].put(STOP_SIGNAL)
                return

            # Set up translation queue and worker
            translation_queue = Queue()
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

            # Process segments using thread pool
            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                futures = []
                for job in jobs:
                    if cancel_event.is_set():
                        print(
                            f"Task {context.task_id} canceled. Stopping job submission."
                        )
                        break
                    futures.append(
                        executor.submit(
                            self.process_segment, job, self.whisper_model, context, translation_queue
                        )
                    )

                # Wait for all futures to complete or until cancellation is detected
                try:
                    wait(futures)
                except Exception as e:
                    print(f"Error while waiting for segment processing: {e}")

            # Signal the translation worker to stop
            translation_queue.put(STOP_SIGNAL)
            translator_thread.join(
                timeout=5
            )  # Allow up to 5 seconds for proper shutdown

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
                cleaned_audio_path = os.path.join(temp_dir, "cleaned_audio.wav")
                
                logger.info("Preparing audio files...")
                prepare_audio(video_path, raw_audio_path, cleaned_audio_path)
                
                # Segment audio
                logger.info("Segmenting audio...")
                segments = segment_audio(cleaned_audio_path, video_path)
                logger.info(f"Created {len(segments)} audio segments")
                
                # Process each segment
                results = []
                for i, segment in enumerate(segments, 1):
                    logger.info(f"Processing segment {i}/{len(segments)}")
                    segment_result = self._process_segment(segment)
                    results.append(segment_result)
                
                logger.info("Video processing completed successfully")
                return {
                    "status": "success",
                    "segments": results
                }
                
        except Exception as e:
            error_msg = f"Error processing video: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "error": error_msg
            }

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
                segment["audio_path"],
                language="en",
                beam_size=5
            )
            
            logger.debug(f"Transcription completed for segment {segment['id']}")
            
            return {
                "id": segment["id"],
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "text": transcription.text
            }
            
        except Exception as e:
            error_msg = f"Error processing segment {segment['id']}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "id": segment["id"],
                "error": error_msg
            }
