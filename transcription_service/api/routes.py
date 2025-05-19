import asyncio
import json
import os
import shutil
import threading
import uuid
from queue import Queue

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse

from .constants import STOP_SIGNAL
from .processor import VideoProcessor
from .translator import Translator
from ..config.context import ProcessingContext
from ..config.transcription_config import TranscriptionConfig
from ..models.model_loader import load_translation_model
from ..utils.aspect import performance_log


def setup_routes(app: FastAPI, processor: VideoProcessor, translator: Translator):
    """Define API routes for health check, transcription, cleanup, and cancellation."""

    @app.get("/health")
    async def health_check():
        return JSONResponse(content={"status": "ok"}, status_code=200)

    @app.post("/transcribe/")
    @performance_log
    async def transcribe_video_streaming(
        file: UploadFile = File(...),
        model_name: str = Form("small"),
        max_workers: int = Form(2),
        min_silence_duration: float = Form(0.7),
        silence_threshold: int = Form(-35),
        language: bool = Form(False),
    ):
        task_id = str(uuid.uuid4())
        output_folder = f"temp/{task_id}"
        os.makedirs(output_folder, exist_ok=True)
        temp_file_path = f"{output_folder}/input_video.mp4"

        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        processor.segment_queues[task_id] = Queue()
        config = TranscriptionConfig(
            model_name, max_workers, min_silence_duration, silence_threshold
        )
        context = ProcessingContext(task_id, temp_file_path, output_folder)

        threading.Thread(
            target=processor.process_video_with_streaming,
            args=(context, config, language, translator),
            daemon=True,
        ).start()

        async def stream_transcription_results():
            queue = processor.segment_queues[task_id]
            try:
                while True:
                    if processor.cancel_events.get(task_id, threading.Event()).is_set():
                        print(f"Task {task_id} canceled. Stopping stream.")
                        yield json.dumps(
                            {"status": "cancelled", "message": "Task cancelled by user"}
                        ) + "\n"
                        break
                    try:
                        result = queue.get(timeout=0.1)
                        if result is STOP_SIGNAL:
                            break
                        yield json.dumps(result) + "\n"
                        await asyncio.sleep(0)
                    except Exception:
                        await asyncio.sleep(0.1)
            finally:
                # Ensure we clean up resources if the client disconnects
                if task_id in processor.cancel_events:
                    processor.cancel_events[task_id].set()
                print(f"Stream for task {task_id} ended")

        return StreamingResponse(
            stream_transcription_results(),
            media_type="application/json",
            headers={"task_id": task_id},
        )

    @app.post("/cancel/{task_id}")
    @performance_log
    async def cancel_task(task_id: str):
        try:
            if task_id in processor.cancel_events:
                # Set the cancellation event
                processor.cancel_events[task_id].set()

                # Add a small delay to ensure the event is recognized
                await asyncio.sleep(0.1)

                # Put a message in the queue to indicate cancellation
                if task_id in processor.segment_queues:
                    processor.segment_queues[task_id].put(
                        {"status": "cancelled", "message": "Task cancelled by user"}
                    )

                return {"message": f"Task {task_id} cancellation initiated."}
            return {"error": f"Task {task_id} not found."}, 404
        except Exception as e:
            return {"error": f"Error cancelling task: {str(e)}"}, 500

    @app.delete("/cleanup/{task_id}")
    @performance_log
    async def cleanup_task(task_id: str):
        try:
            # Make sure the task is cancelled first
            if task_id in processor.cancel_events:
                processor.cancel_events[task_id].set()
                # Small delay to ensure cancellation is processed
                await asyncio.sleep(0.1)

            # Clean up resources
            output_folder = f"temp/{task_id}"
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)

            # Remove from queues
            processor.segment_queues.pop(task_id, None)

            # Clean up cancel event
            with processor.cancel_events_lock:
                processor.cancel_events.pop(task_id, None)

            return {"message": f"Task {task_id} cleaned up successfully"}
        except Exception as e:
            return {"error": f"Error cleaning up task: {str(e)}"}, 500

    @app.on_event("startup")
    @performance_log
    async def startup_event():
        os.makedirs("temp", exist_ok=True)
        translator.nmt_model, translator.tokenizer = load_translation_model()
