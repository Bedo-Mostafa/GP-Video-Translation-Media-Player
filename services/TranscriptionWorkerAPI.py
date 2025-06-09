from os import path
import os
import re
from PySide6.QtCore import QThread, Signal
from json import loads, JSONDecodeError
from filelock import FileLock
from utils.config import get_transcript_file
from services.TranscriptionClient import TranscriptionClient
from services.utils.context_manager import ContextManager
from utils.logging_config import setup_logging


class TranscriptionWorkerAPI(QThread):
    finished = Signal(str)
    receive_first_segment = Signal(str)
    progress = Signal(str)
    error = Signal(str)

    def __init__(
        self, video_file=None, src_lang=None, tgt_lang=None, transcription_server=None
    ):
        super().__init__()
        self.logger = setup_logging()
        self.video_file = video_file
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.server_port = transcription_server.port if transcription_server else 8000
        self.translate = True if src_lang != tgt_lang else False
        self.transcription_server = transcription_server
        self.client = TranscriptionClient(self.server_port, transcription_server)
        self.task_id = None
        self._is_running = True
        self.lock = None
        self.start_from = 0
        self.segment_counter = 0

    def run(self):
        """Process transcription stream and save segments."""
        try:
            self._prepare_transcription_file()
            self.client.start_server_if_needed()
            self.task_id, response = self.client.upload_video(
                self.video_file,
                self.translate,
                self.src_lang,
                self.tgt_lang,
                self.start_from,
                self.segment_counter,
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
        start_srt = self._seconds_to_srt_time(self.start_from + start_time)
        end_srt = self._seconds_to_srt_time(self.start_from + end_time)
        return f"{counter}\n{start_srt} --> {end_srt}\n{text}\n\n"

    def _seconds_to_srt_time(self, seconds):
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        mill_secs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{mill_secs:03d}"

    def _srt_to_seconds_time(self, srt_time):
        """Convert SRT time format (HH:MM:SS,mmm) to seconds."""
        if srt_time == "0":
            return 0
        match = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", srt_time.strip())
        if match:
            hours, minutes, seconds, milliseconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        raise ValueError(
            f"Invalid SRT time format: {srt_time} of type {type(srt_time)}"
        )

    def _prepare_transcription_file(self):
        """Prepare existing transcription file if it exists."""
        transcript_file = get_transcript_file()
        if path.exists(transcript_file):
            with open(transcript_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            last_index = 0
            last_end_time = None
            i = len(lines) - 1

            # Reverse parse to find last complete subtitle block
            while i >= 2:
                line = lines[i].strip()
                time_line = lines[i - 1].strip()
                index_line = lines[i - 2].strip()

                match = re.match(r".*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", time_line)
                if match and index_line.isdigit():
                    last_index = int(index_line)
                    last_end_time = match.group(1)
                    break

                i -= 1

            self.segment_counter = last_index
            self.start_from = last_end_time

            print(
                f"Resuming from segment {self.segment_counter} at time {self.start_from}"
            )

        else:
            self.segment_counter = 0
            print("No existing transcription file found, starting fresh.")

        self.start_from = self._srt_to_seconds_time(str(self.start_from))

        context = ContextManager.get_context()
        context.start_from = self.start_from
        context.segment_start = self.segment_counter

    def _save_segment(self, text):
        """Save a transcription segment to file."""
        transcript_file = get_transcript_file()
        self.lock = FileLock(get_transcript_file(is_lock=True))

        with self.lock:
            needs_newline = False

            if os.path.exists(transcript_file) and os.path.getsize(transcript_file) > 0:
                with open(transcript_file, "rb") as f:
                    f.seek(-2, os.SEEK_END)
                    last_bytes = f.read(2)
                    if not last_bytes.endswith(b"\n\n"):
                        needs_newline = True

            with open(transcript_file, "a", encoding="utf-8") as f:
                if needs_newline:
                    f.write("\n")
                f.write(text.rstrip() + "\n")
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
        self.wait(5000)
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
