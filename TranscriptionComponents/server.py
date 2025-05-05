import asyncio
import itertools
import json
import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import List, Tuple

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from tqdm import tqdm

from Config.ProcessingContext import ProcessingContext
from Config.TranscriptionConfig import TranscriptionConfig
from TranscriptionComponents.logger import Logger
from TranscriptionComponents.audio_processing import prepare_audio, get_video_duration, segment_audio, create_segment_jobs, cut_audio_segment
from TranscriptionComponents.transcription_utils import transcribe_segment
from TranscriptionComponents.model_loading import load_whisper_model, load_translation_model
from TranscriptionComponents.network_utils import is_port_available


class TranscriptionServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """Initialize the TranscriptionServer."""
        self.host = host
        self.port = port
        self.app = FastAPI(title="Video Transcription Streaming API")
        self.logger = Logger(log_file="transcription_server_log.txt")
        self.segment_queues = {}
        self.model_cache = {}
        self.nmt_model = None
        self.tokenizer = None
        self.server_thread = None
        self.setup_middleware()
        self.setup_routes()

    def setup_middleware(self):
        """Configure CORS middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """Define FastAPI routes."""
        @self.app.get("/health")
        async def health_check():
            return JSONResponse(content={"status": "ok"}, status_code=200)

        @self.app.post("/transcribe/")
        async def transcribe_video_streaming(
            file: UploadFile = File(...),
            model_name: str = Form("small"),
            max_workers: int = Form(4),
            min_silence_duration: float = Form(0.7),
            silence_threshold: int = Form(-35),
            language: bool = Form(False)
        ):
            """Handle video transcription with streaming results."""
            task_id = str(uuid.uuid4())
            output_folder = f"temp/{task_id}"
            os.makedirs(output_folder, exist_ok=True)
            temp_file_path = f"{output_folder}/input_video.mp4"

            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            self.segment_queues[task_id] = Queue()
            config = TranscriptionConfig(
                model_name, max_workers, min_silence_duration, silence_threshold)
            context = ProcessingContext(task_id, temp_file_path, output_folder)

            background_thread = threading.Thread(
                target=self.process_video_with_streaming,
                args=(context, config, language)
            )
            background_thread.daemon = True
            background_thread.start()

            async def stream_transcription_results():
                queue = self.segment_queues[task_id]
                try:
                    while True:
                        try:
                            result = queue.get(block=True, timeout=0.1)
                            if result == "DONE":
                                break
                            yield json.dumps(result) + "\n"
                        except Exception:
                            await asyncio.sleep(0.1)
                finally:
                    if task_id in self.segment_queues:
                        del self.segment_queues[task_id]

            return StreamingResponse(
                stream_transcription_results(),
                media_type="application/json"
            )

        @self.app.delete("/cleanup/{task_id}")
        async def cleanup_task(task_id: str):
            """Clean up task files and resources."""
            output_folder = f"temp/{task_id}"
            if not os.path.exists(output_folder):
                return {"message": "Task files already cleaned up or not found"}

            shutil.rmtree(output_folder)
            if task_id in self.segment_queues:
                del self.segment_queues[task_id]
            return {"message": f"Task {task_id} cleaned up successfully"}

        @self.app.on_event("startup")
        async def startup_event():
            """Perform startup tasks."""
            os.makedirs("temp", exist_ok=True)
            self.nmt_model, self.tokenizer = load_translation_model()

    def prepare_audio_files(self, context: ProcessingContext):
        """Prepare audio files for transcription."""
        start_time = time.time()
        prepare_audio(context.video_path, context.raw_audio_path,
                      context.cleaned_audio_path, self.logger)
        elapsed_time = time.time() - start_time
        self.logger.log_step("Prepare Audio", elapsed_time)

    def load_transcription_model(self, config: TranscriptionConfig):
        """Load the Whisper model for transcription."""
        start_time = time.time()
        model = load_whisper_model(config.model_name)
        elapsed_time = time.time() - start_time
        self.logger.log_step("Load Whisper Model", elapsed_time)
        return model

    def segment_audio_file(self, context: ProcessingContext, config: TranscriptionConfig) -> List[Tuple[float, float]]:
        """Segment audio based on silence detection."""
        start_time = time.time()
        silent_points = segment_audio(
            context.cleaned_audio_path,
            context.video_path,
            config.min_silence_duration,
            config.silence_threshold,
            self.logger
        )
        elapsed_time = time.time() - start_time
        self.logger.log_step("Segment Audio", elapsed_time)
        return silent_points

    def create_jobs(self, context: ProcessingContext, silent_points: List[Tuple[float, float]]) -> List[Tuple[float, float, int]]:
        """Create segment jobs for transcription."""
        start_time = time.time()
        video_duration = get_video_duration(context.video_path)
        jobs = create_segment_jobs(silent_points, video_duration, self.logger)
        elapsed_time = time.time() - start_time
        self.logger.log_step("Create Segment Jobs", elapsed_time)
        return jobs

    def translate_segment(self, segment: dict) -> dict:
        """Translate a segment to Arabic."""
        try:
            translated = self.nmt_model.generate(
                **self.tokenizer(
                    segment["text"],
                    return_tensors="pt",
                    padding=True,
                    truncation=True
                ).to(self.nmt_model.device)
            )
            translated_text = self.tokenizer.decode(
                translated[0], skip_special_tokens=True)
            return {**segment, "text": translated_text}
        except Exception as e:
            print(
                f"Translation failed for segment {segment.get('index PRF: 2')}")
            return {**segment, "text": "[Translation Error]"}

    def translation_worker(self, translation_queue: Queue, context: ProcessingContext, language: bool):
        """Worker thread for translating segments to Arabic."""
        while True:
            segment_to_translate = translation_queue.get()
            if segment_to_translate is ...:  # Stop signal
                break
            if language:
                translated_segment = self.translate_segment(
                    segment_to_translate)
                text = translated_segment["text"]
            else:
                text = segment_to_translate["text"]

            index = segment_to_translate["index"]
            result = {
                "segment_index": index,
                "start_time": segment_to_translate["start"],
                "end_time": segment_to_translate["end"],
                "text": text
            }
            self.segment_queues[context.task_id].put(result)

    def process_segment(self, job: Tuple[float, float, int], model, context: ProcessingContext, translation_queue: Queue):
        """Process a single audio segment."""
        start_time_segment = time.time()
        start_time, end_time, segment_idx = job
        temp_audio_file = os.path.join(
            context.output_folder, f"segment_{segment_idx}_audio.wav")
        try:
            cut_audio_segment(context.cleaned_audio_path,
                              temp_audio_file, start_time, end_time, self.logger)
            adjusted_segments = transcribe_segment(
                model, temp_audio_file, start_time, end_time)
            for segment in adjusted_segments:
                index = next(itertools.count(1))
                segment_with_index = {**segment, "index": index}
                translation_queue.put(segment_with_index)
        except Exception as e:
            print(f"Error processing segment {segment_idx}: {str(e)}")
        finally:
            if os.path.exists(temp_audio_file):
                try:
                    os.remove(temp_audio_file)
                except:
                    pass
            elapsed_time_segment = time.time() - start_time_segment
            self.logger.log_step(
                f"Process Segment {segment_idx}",
                elapsed_time_segment,
                additional_info=f"Start Time: {start_time:.2f}s, End Time: {end_time:.2f}s"
            )

    def process_video_with_streaming(self, context: ProcessingContext, config: TranscriptionConfig, language: bool):
        """Process video with streaming transcription and translation."""
        try:
            self.prepare_audio_files(context)
            model = self.load_transcription_model(config)
            silent_points = self.segment_audio_file(context, config)
            jobs = self.create_jobs(context, silent_points)

            translation_queue = Queue()
            stop_signal = ...

            translator_thread = threading.Thread(
                target=self.translation_worker,
                args=(translation_queue, context, language)
            )
            translator_thread.daemon = True
            translator_thread.start()

            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                list(tqdm(
                    executor.map(lambda job: self.process_segment(
                        job, model, context, translation_queue), jobs),
                    total=len(jobs),
                    desc="Transcribing segments"
                ))

            translation_queue.put(stop_signal)
            translator_thread.join()
            self.segment_queues[context.task_id].put("DONE")

        except Exception as e:
            print(f"Error in video processing: {e}")
            if context.task_id in self.segment_queues:
                self.segment_queues[context.task_id].put(
                    {"status": "error", "message": str(e)})
                self.segment_queues[context.task_id].put("DONE")

    def start(self):
        """Start the transcription server."""
        if self.server_thread is None or not self.server_thread.is_alive():
            port = self.port
            while not is_port_available(port):
                print(f"Port {port} is in use, trying {port + 1}")
                port += 1
            self.port = port
            self.server_thread = threading.Thread(
                target=self.run_api, daemon=True)
            self.server_thread.start()
            print(
                f"Transcription server started at http://{self.host}:{self.port}")
        else:
            print("Server is already running.")

    def run_api(self):
        """Run the FastAPI application."""
        uvicorn.run(self.app, host=self.host, port=self.port)

    def stop(self):
        """Stop the transcription server."""
        if self.server_thread and self.server_thread.is_alive():
            print("Stopping transcription server...")
            self.server_thread = None
            print("Transcription server stopped.")
