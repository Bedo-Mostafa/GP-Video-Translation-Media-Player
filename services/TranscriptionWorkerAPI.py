from os import path, remove
from PySide6.QtCore import QThread, Signal
from json import loads, JSONDecodeError
from filelock import FileLock
from utils.config import TRANSCRIPT_FILE, TRANSCRIPT_LOCK_FILE
from services.TranscriptionClient import TranscriptionClient
from utils.logging_config import setup_logging


class TranscriptionWorkerAPI(QThread):
    finished = Signal(str)
    receive_first_segment = Signal(str)
    progress = Signal(str)
    error = Signal(str)

    def __init__(self, video_file=None, language=None, transcription_server=None):
        super().__init__()
        self.logger = setup_logging()
        self.video_file = video_file
        self.server_port = transcription_server.port if transcription_server else 8000
        self.translate = language
        self.transcription_server = transcription_server
        self.client = TranscriptionClient(self.server_port, transcription_server)
        self.task_id = None
        self._is_running = True
        self.lock = FileLock(TRANSCRIPT_LOCK_FILE)
        self.segment_counter = 0

    def run(self):
        """Process transcription stream and save segments."""
        try:
            self._prepare_transcription_file()
            self.client.start_server_if_needed()
            self.task_id, response = self.client.upload_video(
                self.video_file,
                self.translate,
                self.progress.emit,
                lambda: not self._is_running,
            )
            is_first_segment = True
            for line in response.iter_lines():
                if not self._is_running:
                    break
                if line:
                    try:
                        segment = loads(line)
                        if "status" in segment:
                            self._handle_status(segment)
                            continue
                        segment["start"] = round(segment.get("start", 0), 3)
                        segment["end"] = round(segment.get("end", 0), 3)

                        # Format as SRT
                        self.segment_counter += 1
                        srt_text = self._format_srt_segment(
                            self.segment_counter,
                            segment["start"],
                            segment["end"],
                            segment["text"],
                        )

                        self._save_segment(srt_text)
                        if is_first_segment:
                            self.receive_first_segment.emit("First Segment Received")
                            is_first_segment = False
                        # self.progress.emit(
                        #     f"Segment {self.segment_counter}: {segment['text']}"
                        # )
                    except JSONDecodeError:
                        self.logger.error("Failed to decode JSON: %s", line)
                    except Exception as e:
                        self.error.emit(f"Streaming decode error: {e}")
            if self._is_running:
                self.finished.emit("Transcription completed and saved.")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._cleanup()

    def _format_srt_segment(self, counter, start_time, end_time, text):
        """Format a segment in SRT format."""
        start_srt = self._seconds_to_srt_time(start_time)
        end_srt = self._seconds_to_srt_time(end_time)
        return f"{counter}\n{start_srt} --> {end_srt}\n{text}\n\n"

    def _seconds_to_srt_time(self, seconds):
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        mill_secs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{mill_secs:03d}"

    def _prepare_transcription_file(self):
        """Delete existing transcription file if it exists."""
        if path.exists(TRANSCRIPT_FILE):
            remove(TRANSCRIPT_FILE)
            self.logger.info("Deleted existing transcription file: %s", TRANSCRIPT_FILE)
        self.segment_counter = 0

    def _save_segment(self, text):
        """Save a transcription segment to file."""
        with self.lock:
            with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
                f.write(text)
                f.flush()
            self.logger.debug("Saved SRT transcription segment: %s", text.strip())

    def _handle_status(self, segment):
        """Handle status messages from the server."""
        if segment["status"] == "cancelled":
            self.logger.info("Task cancelled: %s", segment.get("message", ""))
        elif segment["status"] == "error":
            self.error.emit(f"Server error: {segment.get('message', 'Unknown error')}")

    def stop(self):
        """Stop the transcription process and cleanup."""
        self.logger.info("Stopping transcription worker")
        self._is_running = False
        if self.task_id:
            self.client.cancel_task(self.task_id)
            self.client.cleanup_task(self.task_id)
        self.client.close_response()
        self.wait(timeout=5000)
        self.logger.info("Transcription worker stopped")

    def _cleanup(self):
        """Clean up resources after transcription."""
        self.client.close_response()
        self.task_id = None
        if self.transcription_server and not getattr(
            self.transcription_server, "persistent", False
        ):
            self.transcription_server.stop()
            self.logger.info("Transcription server stopped")
