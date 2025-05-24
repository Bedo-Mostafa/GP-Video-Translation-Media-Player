from threading import Thread
from os import path, makedirs
from atexit import register
from shutil import rmtree
from uvicorn import Config, Server
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.VideoProcessor import VideoProcessor
from services.api.routes import setup_routes
from services.transcription.translator import Translator
from services.utils.network import is_port_available
from services.utils.logging_config import get_processor_logger

logger = get_processor_logger()


class TranscriptionServer:
    """FastAPI server for streaming video transcription and translation."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """Initialize the transcription server.

        Args:
            host: Host address to bind the server to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title="Video Transcription Streaming API")
        self.processor = VideoProcessor()
        self.translator = Translator()
        self.server_thread = None
        self.uvicorn_server = (
            None  # To manage the uvicorn server instance for graceful shutdown
        )

        # Set up the application
        self.setup_middleware()
        setup_routes(self.app, self.processor, self.translator)

        # Register cleanup handler
        register(self.cleanup)

        logger.info("TranscriptionServer initialized")

    def setup_middleware(self):

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )  #
        logger.debug("CORS middleware configured")

    def start(self):  #
        """Start the FastAPI server."""
        if not self.server_thread or not self.server_thread.is_alive():
            while not is_port_available(self.port):
                logger.warning(f"Port {self.port} in use, trying next...")
                self.port += 1

            makedirs("temp", exist_ok=True)  # Ensures temp dir for uploads

            self.server_thread = Thread(target=self.run_api, daemon=True)
            self.server_thread.start()
            logger.info(f"Server started at http://{self.host}:{self.port}")
        else:  #
            logger.info("Server already running.")

    def run_api(self):  #
        """Run the Uvicorn server."""
        config = Config(
            self.app, host=self.host, port=self.port, log_level="info"
        )
        self.uvicorn_server = Server(config)  # Store server instance
        try:
            # uvicorn.run(self.app, host=self.host, port=self.port, log_level="info") # Original
            self.uvicorn_server.run()  # Use server instance run
        except Exception as e:
            logger.error(f"Error running server: {e}", exc_info=True)

    def stop(self):
        """Stop the FastAPI server and cancel tasks."""
        logger.info("Initiating transcription server shutdown...")

        # Cancel all active transcription tasks
        self._cancel_all_tasks()

        if self.uvicorn_server:
            logger.info(
                "Uvicorn server shutdown will occur when main process exits or via signal."
            )

        if self.server_thread and self.server_thread.is_alive():
            logger.info(
                "Transcription server thread is alive, relying on daemon property for exit."
            )
            # self.server_thread = None # Not strictly stopping the thread here, but de-referencing

        logger.info("Transcription server shutdown process initiated.")

    def _cancel_all_tasks(self):
        """Cancel all active transcription tasks."""
        with self.processor.task_manager.cancel_events_lock:
            task_ids = list(self.processor.task_manager.cancel_events.keys())

        if not task_ids:
            logger.info("No active tasks to cancel during server shutdown.")
            return

        logger.info(
            f"Cancelling {len(task_ids)} active tasks during server shutdown: {task_ids}"
        )
        for task_id in task_ids:
            try:
                logger.info(f"Cancelling task {task_id} during server shutdown")
                self.processor.task_manager.cancel_task(task_id)
            except Exception as e:
                logger.error(f"Error cancelling task {task_id}: {e}")

    def cleanup(self):
        """Clean up resources when the server is shut down (called by atexit)."""
        logger.info("Cleaning up server resources via atexit...")
        self.stop()  # Call stop to cancel tasks

        # Remove temporary files directory
        try:
            temp_dir_path = "temp"
            if path.exists(temp_dir_path):
                rmtree(temp_dir_path)
                logger.info(f"Removed temporary directory: {temp_dir_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")
        logger.info("Server cleanup finished.")
