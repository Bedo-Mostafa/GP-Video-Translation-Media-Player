
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

STOP_SIGNAL = object()


class TranscriptionServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.app = FastAPI(title="Video Transcription Streaming API")
        self.logger = Logger(log_file="transcription_server_log.txt")
        self.segment_queues = {}
        self.model_cache = {}
        self.nmt_model = None
        self.tokenizer = None
        self.server_thread = None
        self.segment_index_counter = itertools.count()
        self.setup_middleware()
        self.setup_routes()

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
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

            threading.Thread(
                target=self.process_video_with_streaming,
                args=(context, config, language),
                daemon=True
            ).start()

            async def stream_transcription_results():
                queue = self.segment_queues[task_id]
                try:
                    while True:
                        try:
                            result = queue.get(timeout=0.1)
                            if result is STOP_SIGNAL:
                                break
                            yield json.dumps(result) + "\n"
                            await asyncio.sleep(0)
                        except Exception:
                            await asyncio.sleep(0.1)
                finally:
                    self.segment_queues.pop(task_id, None)

            return StreamingResponse(stream_transcription_results(), media_type="application/json")

        @self.app.delete("/cleanup/{task_id}")
        async def cleanup_task(task_id: str):
            output_folder = f"temp/{task_id}"
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            self.segment_queues.pop(task_id, None)
            return {"message": f"Task {task_id} cleaned up successfully"}

        @self.app.on_event("startup")
        async def startup_event():
            os.makedirs("temp", exist_ok=True)
            self.nmt_model, self.tokenizer = load_translation_model()

    def prepare_audio_files(self, context: ProcessingContext):
        start_time = time.time()
        prepare_audio(context.video_path, context.raw_audio_path,
                      context.cleaned_audio_path, self.logger)
        self.logger.log_step("Prepare Audio", time.time() - start_time)

    def load_transcription_model(self, config: TranscriptionConfig):
        if config.model_name in self.model_cache:
            return self.model_cache[config.model_name]
        start_time = time.time()
        model = load_whisper_model(config.model_name)
        self.logger.log_step("Load Whisper Model", time.time() - start_time)
        self.model_cache[config.model_name] = model
        return model

    def segment_audio_file(self, context: ProcessingContext, config: TranscriptionConfig):
        start_time = time.time()
        silent_points = segment_audio(context.cleaned_audio_path, context.video_path,
                                      config.min_silence_duration, config.silence_threshold, self.logger)
        self.logger.log_step("Segment Audio", time.time() - start_time)
        return silent_points

    def create_jobs(self, context: ProcessingContext, silent_points: List[Tuple[float, float]]):
        start_time = time.time()
        jobs = create_segment_jobs(
            silent_points, get_video_duration(context.video_path), self.logger)
        self.logger.log_step("Create Segment Jobs", time.time() - start_time)
        return jobs

    def translate_segment(self, segment: dict):
        try:
            translated = self.nmt_model.generate(
                **self.tokenizer(segment["text"], return_tensors="pt", padding=True, truncation=True).to(self.nmt_model.device))
            return {**segment, "text": self.tokenizer.decode(translated[0], skip_special_tokens=True)}
        except Exception:
            return {**segment, "text": "[Translation Error]"}

    def translation_worker(self, translation_queue: Queue, context: ProcessingContext, language: bool):
        while True:
            segment = translation_queue.get()
            if segment is STOP_SIGNAL:
                break
            if language:
                segment = self.translate_segment(segment)
            self.segment_queues[context.task_id].put({
                "segment_index": segment["index"],
                "start_time": segment["start"],
                "end_time": segment["end"],
                "text": segment["text"]
            })
            translation_queue.task_done()

    def process_segment(self, job: Tuple[float, float, int], model, context: ProcessingContext, translation_queue: Queue):
        start_time, end_time, segment_idx = job
        temp_audio_file = os.path.join(
            context.output_folder, f"segment_{segment_idx}_audio.wav")
        try:
            cut_audio_segment(context.cleaned_audio_path,
                              temp_audio_file, start_time, end_time, self.logger)
            adjusted_segments = transcribe_segment(
                model, temp_audio_file, start_time, end_time)
            for segment in adjusted_segments:
                segment["index"] = next(self.segment_index_counter)
                translation_queue.put(segment)
        except Exception as e:
            print(f"Error processing segment {segment_idx}: {str(e)}")
        finally:
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            self.logger.log_step(f"Process Segment {segment_idx}", time.time(
            ) - start_time, additional_info=f"Start: {start_time:.2f}s, End: {end_time:.2f}s")

    def process_video_with_streaming(self, context: ProcessingContext, config: TranscriptionConfig, language: bool):
        try:
            self.prepare_audio_files(context)
            model = self.load_transcription_model(config)
            jobs = self.create_jobs(
                context, self.segment_audio_file(context, config))

            translation_queue = Queue()
            translator_thread = threading.Thread(target=self.translation_worker, args=(
                translation_queue, context, language), daemon=True)
            translator_thread.start()

            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                list(tqdm(executor.map(lambda job: self.process_segment(job, model, context,
                     translation_queue), jobs), total=len(jobs), desc="Transcribing segments"))

            translation_queue.put(STOP_SIGNAL)
            translator_thread.join()
            self.segment_queues[context.task_id].put(STOP_SIGNAL)
        except Exception as e:
            print(f"Error in video processing: {e}")
            self.segment_queues[context.task_id].put(
                {"status": "error", "message": str(e)})
            self.segment_queues[context.task_id].put(STOP_SIGNAL)

    def start(self):
        if not self.server_thread or not self.server_thread.is_alive():
            while not is_port_available(self.port):
                print(f"Port {self.port} in use, trying next...")
                self.port += 1
            self.server_thread = threading.Thread(
                target=self.run_api, daemon=True)
            self.server_thread.start()
            print(f"Server started at http://{self.host}:{self.port}")
        else:
            print("Server already running.")

    def run_api(self):
        uvicorn.run(self.app, host=self.host, port=self.port)

    def stop(self):
        if self.server_thread and self.server_thread.is_alive():
            print("Stopping transcription server...")
            self.server_thread = None
            print("Transcription server stopped.")
