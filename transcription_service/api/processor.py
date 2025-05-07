import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import List, Tuple

from tqdm import tqdm

from .constants import STOP_SIGNAL
from ..audio.processing import prepare_audio
from ..audio.segmentation import segment_audio, create_segment_jobs, cut_audio_segment
from ..config.context import ProcessingContext
from ..config.transcription_config import TranscriptionConfig
from ..models.model_loader import load_whisper_model
from ..utils.logger import Logger
from ..utils.transcription import transcribe_segment
from .translator import Translator


class VideoProcessor:
    """Handles video processing, audio segmentation, and transcription."""

    def __init__(self, logger: Logger):
        self.logger = logger
        self.segment_queues = {}
        self.model_cache = {}
        self.cancel_events = {}
        self.cancel_events_lock = threading.Lock()

    def prepare_audio_files(self, context: ProcessingContext):
        """Prepare audio files by extracting and cleaning audio from video."""
        start_time = time.time()
        prepare_audio(context.video_path, context.raw_audio_path,
                      context.cleaned_audio_path, self.logger)
        self.logger.log_step("Prepare Audio", time.time() - start_time)

    def load_transcription_model(self, config: TranscriptionConfig):
        """Load or retrieve cached Whisper model."""
        if config.model_name in self.model_cache:
            return self.model_cache[config.model_name]
        start_time = time.time()
        model = load_whisper_model(config.model_name)
        self.logger.log_step("Load Whisper Model", time.time() - start_time)
        self.model_cache[config.model_name] = model
        return model

    def segment_audio_file(self, context: ProcessingContext, config: TranscriptionConfig):
        """Segment audio based on silent points."""
        start_time = time.time()
        silent_points = segment_audio(
            context.cleaned_audio_path, context.video_path,
            config.min_silence_duration, config.silence_threshold, self.logger
        )
        self.logger.log_step("Segment Audio", time.time() - start_time)
        return silent_points

    def create_jobs(self, context: ProcessingContext, silent_points: List[float]):
        """Create transcription jobs from silent points."""
        start_time = time.time()
        jobs = create_segment_jobs(
            silent_points, context.get_video_duration(), self.logger
        )
        self.logger.log_step("Create Segment Jobs", time.time() - start_time)
        return jobs

    def process_segment(self, job: Tuple[float, float, int], model, context: ProcessingContext, translation_queue: Queue):
        """Process a single audio segment for transcription."""
        start_time, end_time, segment_idx = job
        temp_audio_file = os.path.join(
            context.output_folder, f"segment_{segment_idx}_audio.wav")
        try:
            if self.cancel_events.get(context.task_id, threading.Event()).is_set():
                print(
                    f"Task {context.task_id} canceled. Stopping segment processing.")
                return
            cut_audio_segment(context.cleaned_audio_path,
                              temp_audio_file, start_time, end_time, self.logger)
            adjusted_segments = transcribe_segment(
                model, temp_audio_file, start_time, end_time)
            for segment in adjusted_segments:
                if self.cancel_events.get(context.task_id, threading.Event()).is_set():
                    print(
                        f"Task {context.task_id} canceled. Stopping segment processing.")
                    return
                segment["index"] = segment_idx
                translation_queue.put(segment)
        except Exception as e:
            print(f"Error processing segment {segment_idx}: {str(e)}")
        finally:
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            self.logger.log_step(
                f"Process Segment {segment_idx}", time.time() - start_time,
                additional_info=f"Start: {start_time:.2f}s, End: {end_time:.2f}s"
            )

    def process_video_with_streaming(self, context: ProcessingContext, config: TranscriptionConfig, language: bool, translator: Translator):
        """Process video for transcription and streaming results."""
        try:
            cancel_event = threading.Event()
            with self.cancel_events_lock:
                self.cancel_events[context.task_id] = cancel_event
            self.prepare_audio_files(context)
            model = self.load_transcription_model(config)
            jobs = self.create_jobs(
                context, self.segment_audio_file(context, config))
            translation_queue = Queue()
            translator_thread = threading.Thread(
                target=translator.transcribe_worker,
                args=(translation_queue, context, language,
                      self.segment_queues, self.cancel_events),
                daemon=True
            )
            translator_thread.start()
            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                for job in tqdm(jobs, total=len(jobs), desc="Transcribing segments"):
                    if cancel_event.is_set():
                        print(
                            f"Task {context.task_id} canceled. Stopping executor.")
                        break
                    executor.submit(self.process_segment, job,
                                    model, context, translation_queue)
            translation_queue.put(STOP_SIGNAL)
            translator_thread.join()
            if context.task_id in self.segment_queues:
                self.segment_queues[context.task_id].put(STOP_SIGNAL)
        except Exception as e:
            print(f"Error in video processing: {e}")
            if context.task_id in self.segment_queues:
                self.segment_queues[context.task_id].put(
                    {"status": "error", "message": str(e)})
                self.segment_queues[context.task_id].put(STOP_SIGNAL)
        finally:
            with self.cancel_events_lock:
                self.cancel_events.pop(context.task_id, None)
            if os.path.exists(context.output_folder):
                shutil.rmtree(context.output_folder)
