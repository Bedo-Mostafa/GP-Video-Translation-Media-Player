from PySide6.QtCore import QThread, Signal
import requests
import os
import json
from filelock import FileLock
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
import time


class TranscriptionWorkerAPI(QThread):
    finished = Signal(str)   # Emitted when all transcription is done
    # Emitted when first segment transcription is done
    receive_first_segment = Signal(str)
    progress = Signal(str)   # Emitted as segments stream in
    error = Signal(str)      # Emitted on any error

    def __init__(self, video_file, language, transcription_server):
        super().__init__()
        self.video_file = video_file
        # Use the server's port if provided, otherwise default to 8000
        self.api_url = f"http://localhost:{transcription_server.port if transcription_server else 800}/transcribe/"
        self.translate = language
        self.transcript_filename = "transcription.txt"
        self.lock = FileLock(self.transcript_filename + ".lock")
        self.is_first_segment = True
        self._is_running = True
        # Reference to TranscriptionServer instance
        self.transcription_server = transcription_server

    def run(self):
        try:
            # Start the transcription server if provided
            if self.transcription_server:
                self.transcription_server.start()
                # Wait for the server to be ready
                max_attempts = 30  # Wait up to 30 seconds (30 * 1s)
                attempt = 0
                while attempt < max_attempts:
                    try:
                        response = requests.get(
                            f"http://localhost:{self.transcription_server.port}/health", timeout=2)
                        if response.status_code == 200:
                            print(
                                f"Server is ready on port {self.transcription_server.port}")
                            break
                    except requests.exceptions.RequestException:
                        attempt += 1
                        time.sleep(1)  # Wait 1 second before retrying
                        if attempt == max_attempts:
                            self.error.emit(
                                "Server failed to start within the timeout period.")
                            return
                    else:
                        break

            if os.path.exists(self.transcript_filename):
                os.remove(self.transcript_filename)
                print(f"{self.transcript_filename} has been deleted.")

            with open(self.video_file, "rb") as f:
                encoder = MultipartEncoder(
                    fields={
                        "file": (os.path.basename(self.video_file), f, "video/mp4"),
                        "model_name": "small",
                        "max_workers": "1",
                        "min_silence_duration": "0.7",
                        "silence_threshold": "-35",
                        "language": str(self.translate).lower()
                    }
                )

                def callback(monitor):
                    if not self._is_running:
                        monitor.abort()
                    percent = int((monitor.bytes_read / monitor.len) * 100)
                    self.progress.emit(f"Uploading: {percent}%")

                monitor = MultipartEncoderMonitor(encoder, callback)
                headers = {"Content-Type": monitor.content_type}

                response = requests.post(
                    self.api_url,
                    data=monitor,
                    headers=headers,
                    stream=True,
                    timeout=600
                )

                if response.status_code != 200:
                    self.error.emit(f"API Error: {response.text}")
                    return

                for line in response.iter_lines():
                    if not self._is_running:
                        break
                    if line:
                        try:
                            segment = json.loads(line)
                            segment["start_time"] = round(
                                segment.get("start_time", 0), 3)
                            segment["end_time"] = round(
                                segment.get("end_time", 0), 3)
                            text = f"[{segment['start_time']} - {segment['end_time']}] {segment['text']}\n"

                            with self.lock:
                                with open(self.transcript_filename, "a", encoding="utf-8") as f:
                                    f.write(text)
                                    f.flush()
                            if self.is_first_segment:
                                self.receive_first_segment.emit(
                                    "First Segment Received")
                                self.is_first_segment = False

                            self.progress.emit(text)
                        except Exception as e:
                            self.error.emit(f"Streaming decode error: {e}")

            self.finished.emit("Transcription completed and saved.")

        except Exception as e:
            self.error.emit(f"Request failed: {str(e)}")
        finally:
            # Stop the server if it was started
            if self.transcription_server:
                self.transcription_server.stop()

    def stop(self):
        """Stop the transcription process and cleanup."""
        print("Stopping transcription worker...")
        self._is_running = False
        self.terminate()
        self.wait()
        print("Transcription worker stopped.")
