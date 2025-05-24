from requests import get, post, delete
from requests.exceptions import RequestException, ConnectionError, Timeout
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from utils.config import (
    API_BASE_URL,
    UPLOAD_TIMEOUT,
    CANCEL_TIMEOUT,
    SERVER_HEALTH_CHECK_TIMEOUT,
    SERVER_START_MAX_ATTEMPTS,
)
from time import sleep
from os import path
from utils.logging_config import setup_logging


class TranscriptionClient:
    """Handles HTTP communication with the transcription server."""

    def __init__(self, server_port, transcription_server=None):
        self.logger = setup_logging()
        self.server_port = server_port
        self.api_url = API_BASE_URL.format(port=server_port)
        self.transcription_server = transcription_server
        self.response = None

    def start_server_if_needed(self):
        """Start the transcription server and verify it's ready."""
        if not self.transcription_server:
            return
        self.logger.info("Starting transcription server on port %s", self.server_port)
        self.transcription_server.start()
        for attempt in range(SERVER_START_MAX_ATTEMPTS):
            try:
                response = get(
                    f"{self.api_url}/health", timeout=SERVER_HEALTH_CHECK_TIMEOUT
                )
                if response.status_code == 200:
                    self.logger.info("Transcription server is ready")
                    return
            except RequestException:
                sleep(1)
            if attempt == SERVER_START_MAX_ATTEMPTS - 1:
                raise RuntimeError("Transcription server failed to start")

    def upload_video(
        self, video_file, enable_translation, progress_callback, abort_check
    ):
        """Upload video file to the transcription server."""
        try:
            with open(video_file, "rb") as f:
                encoder = MultipartEncoder(
                    fields={
                        "file": (path.basename(video_file), f, "video/mp4"),
                        "enable_translation": "True" if enable_translation else "False",
                    }
                )

                def callback(monitor):
                    if abort_check():
                        monitor.abort()
                    percent = int((monitor.bytes_read / monitor.len) * 100)
                    progress_callback(f"Uploading: {percent}%")

                monitor = MultipartEncoderMonitor(encoder, callback)
                headers = {"Content-Type": monitor.content_type}
                self.response = post(
                    f"{self.api_url}/transcribe/",
                    data=monitor,
                    headers=headers,
                    stream=True,
                    timeout=UPLOAD_TIMEOUT,
                )
                task_id = self.response.headers.get("task_id")
                self.logger.info("Started transcription task with ID: %s", task_id)
                if self.response.status_code != 200:
                    raise RuntimeError(f"API Error: {self.response.text}")
                return task_id, self.response
        except ConnectionError as e:
            raise RuntimeError(
                f"Connection error: {str(e)}. Is the server running?"
            ) from e
        except Timeout as e:
            raise RuntimeError("Request timed out. Server may be overloaded.") from e
        except Exception as e:
            raise RuntimeError(f"Upload failed: {str(e)}") from e

    def cancel_task(self, task_id):
        """Send cancellation request for a specific task."""
        try:
            response = post(f"{self.api_url}/cancel/{task_id}", timeout=CANCEL_TIMEOUT)
            if response.status_code == 200:
                self.logger.info("Task %s cancellation initiated", task_id)
            else:
                self.logger.error(
                    "Failed to cancel task %s: %s", task_id, response.text
                )
        except Exception as e:
            self.logger.error("Error cancelling task %s: %s", task_id, str(e))

    def cleanup_task(self, task_id):
        """Send cleanup request for a specific task."""
        try:
            response = delete(
                f"{self.api_url}/cleanup/{task_id}", timeout=CANCEL_TIMEOUT
            )
            if response.status_code == 200:
                self.logger.info("Task %s cleaned up successfully", task_id)
            else:
                self.logger.error(
                    "Failed to clean up task %s: %s", task_id, response.text
                )
        except Exception as e:
            self.logger.error("Error cleaning up task %s: %s", task_id, str(e))

    def close_response(self):
        """Close the active response object."""
        if self.response:
            try:
                self.response.close()
                self.logger.info("Closed response object")
            except Exception as e:
                self.logger.error("Error closing response: %s", str(e))
            self.response = None
