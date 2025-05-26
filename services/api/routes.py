from asyncio import sleep
from json import dumps
from os import makedirs, path
from shutil import rmtree, copyfileobj
from threading import Thread
from uuid import uuid4
from queue import Empty as QueueEmpty

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse

from services.api.constants import STOP_SIGNAL
from services.api.VideoProcessor import VideoProcessor
from services.transcription.translator import Translator
from services.config.context import ProcessingContext
from services.models.model_loader import load_translation_model
from services.utils.aspect import performance_log
from utils.logging_config import get_component_logger

logger = get_component_logger("video_processor")


def setup_routes(app: FastAPI, processor: VideoProcessor, translator: Translator):
    @app.get("/health")
    async def health_check():
        return JSONResponse(content={"status": "ok"}, status_code=200)

    @app.post("/transcribe/")
    @performance_log
    async def transcribe_video_streaming(
        file: UploadFile = File(...),
        enable_translation: bool = Form(False),  # Changed from 'language'
    ):
        task_id = str(uuid4())
        output_folder = f"temp/{task_id}"  # For initial video save
        makedirs(output_folder, exist_ok=True)
        temp_file_path = f"{output_folder}/input_video.mp4"

        with open(temp_file_path, "wb") as buffer:
            copyfileobj(file.file, buffer)

        client_output_queue, _ = processor.task_manager.register_task(task_id)

        context = ProcessingContext(task_id, temp_file_path, output_folder)

        Thread(
            target=processor.process_video_with_streaming,
            args=(
                context,
                enable_translation,
                translator,
            ),
            daemon=True,
        ).start()

        async def stream_transcription_results():
            # [ Stream consumption logic from previous routes.py is largely okay ]
            # It reads from client_output_queue and sends JSON lines.
            # Ensure it handles STOP_SIGNAL and potential error dicts correctly.
            try:
                while True:
                    if processor.task_manager.is_cancelled(task_id):
                        logger.info(
                            f"Task {task_id} cancelled by server. Stopping client stream."
                        )
                        yield dumps(
                            {
                                "status": "cancelled",
                                "message": "Task cancelled by server",
                            }
                        ) + "\n"
                        break
                    try:
                        result = client_output_queue.get(
                            timeout=0.1
                        )  # Timeout to check cancellation

                        if result is STOP_SIGNAL:
                            logger.info(
                                f"Task {task_id} (ClientStream): Received STOP_SIGNAL. Ending stream."
                            )
                            break

                        yield dumps(result) + "\n"
                        if isinstance(result, dict) and result.get("status") in [
                            "error",
                            "cancelled",
                        ]:
                            logger.info(
                                f"Task {task_id} (ClientStream): Stream ending due to status: {result['status']}"
                            )
                            break

                        await sleep(0)  # Yield control for other async tasks in FastAPI
                    except QueueEmpty:
                        await sleep(0.1)
                    except Exception as e:
                        logger.error(
                            f"Error streaming transcription results for task {task_id}: {e}",
                            exc_info=True,
                        )
                        try:
                            yield dumps(
                                {
                                    "status": "error",
                                    "message": "Streaming error occurred on server",
                                }
                            ) + "\n"
                        except Exception as send_err:
                            logger.error(
                                f"Failed to send streaming error to client for task {task_id}: {send_err}"
                            )
                        break
            finally:
                logger.info(
                    f"Stream for task {task_id} ended on server side (routes.py)."
                )
                # If stream ends prematurely (e.g. client disconnect), try to cancel the backend task.
                if not processor.task_manager.is_cancelled(task_id):
                    logger.warning(
                        f"Client for task {task_id} likely disconnected or stream ended. Initiating task cancellation."
                    )
                    processor.task_manager.cancel_task(task_id)

        return StreamingResponse(
            stream_transcription_results(),
            media_type="application/json",
            headers={"task_id": task_id},
        )

    @app.post("/cancel/{task_id}")
    @performance_log
    async def cancel_task_endpoint(task_id: str):
        try:
            logger.info(f"Received cancellation request for task {task_id} via API.")
            processor.task_manager.cancel_task(task_id)
            await sleep(0.1)
            return {"message": f"Task {task_id} cancellation initiated."}
        except Exception as e:
            logger.error(f"Error cancelling task {task_id} via API: {str(e)}")
            return {"error": f"Error cancelling task: {str(e)}"}, 500

    @app.delete("/cleanup/{task_id}")
    @performance_log
    async def cleanup_task_endpoint(task_id: str):
        try:
            logger.info(f"Received cleanup request for task {task_id} via API.")
            # Ensure task is marked for cancellation so threads can exit
            if not processor.task_manager.is_cancelled(task_id):
                processor.task_manager.cancel_task(task_id)
                await sleep(0.2)  # Give a moment for event to propagate

            # Forcibly clean output folder if it still exists (VideoProcessor might have cleaned it)
            output_folder = f"temp/{task_id}"
            if path.exists(output_folder):
                try:
                    rmtree(output_folder)
                    logger.info(
                        f"Removed output folder {output_folder} for task {task_id} via cleanup endpoint."
                    )
                except Exception as e:
                    logger.error(
                        f"Error removing output folder {output_folder} in cleanup endpoint: {e}"
                    )

            # Call task_manager.cleanup_task again as a final measure,
            # though VideoProcessor should have called it.
            processor.task_manager.cleanup_task(task_id)

            return {"message": f"Task {task_id} cleanup process initiated/verified."}
        except Exception as e:
            logger.error(f"Error cleaning up task {task_id} via API: {str(e)}")
            return {"error": f"Error cleaning up task: {str(e)}"}, 500

    @app.on_event("startup")
    @performance_log
    async def startup_event():
        makedirs("temp", exist_ok=True)
        logger.info("Loading translation model on startup...")
        translator.nmt_model, translator.tokenizer = load_translation_model()
        logger.info("Translation model loaded.")
