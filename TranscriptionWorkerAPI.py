from PySide6.QtCore import QThread, Signal
import requests
import os
import json
from filelock import FileLock
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
import time


class TranscriptionWorkerAPI(QThread):
    finished = Signal(str)  # Emitted when all transcription is done
    receive_first_segment = Signal(
        str
    )  # Emitted when first segment transcription is done
    progress = Signal(str)  # Emitted as segments stream in
    error = Signal(str)  # Emitted on any error

    def __init__(self, video_file, language, transcription_server):
        super().__init__()
        self.video_file = video_file
        # Use the server's port if provided, otherwise default to 8000
        self.server_port = transcription_server.port if transcription_server else 8000
        self.api_url = f"http://localhost:{self.server_port}/transcribe/"
        self.translate = language
        self.transcript_filename = "transcription.txt"
        self.lock = FileLock(self.transcript_filename + ".lock")
        self.is_first_segment = True
        self._is_running = True
        self.task_id = None
        # Reference to TranscriptionServer instance
        self.transcription_server = transcription_server
        # Response object for the streaming request
        self.response = None

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
                            f"http://localhost:{self.server_port}/health",
                            timeout=2,
                        )
                        if response.status_code == 200:
                            print(f"Server is ready on port {self.server_port}")
                            break
                    except requests.exceptions.RequestException:
                        attempt += 1
                        time.sleep(1)  # Wait 1 second before retrying
                        if attempt == max_attempts:
                            self.error.emit(
                                "Server failed to start within the timeout period."
                            )
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
                        "enable_translation": "True" if self.translate else "False",
                    }
                )

                def callback(monitor):
                    if not self._is_running:
                        monitor.abort()
                    percent = int((monitor.bytes_read / monitor.len) * 100)
                    self.progress.emit(f"Uploading: {percent}%")

                monitor = MultipartEncoderMonitor(encoder, callback)
                headers = {"Content-Type": monitor.content_type}

                # Store the response object so we can close it during cancellation
                self.response = requests.post(
                    self.api_url,
                    data=monitor,
                    headers=headers,
                    stream=True,
                    timeout=600,
                )

                # Extract and store the task_id
                self.task_id = self.response.headers.get("task_id")
                print(f"Started transcription task with ID: {self.task_id}")

                if self.response.status_code != 200:
                    self.error.emit(f"API Error: {self.response.text}")
                    return

                for line in self.response.iter_lines():
                    if not self._is_running:
                        break
                    if line:
                        try:
                            segment = json.loads(line)

                            # Check if this is a status message
                            if "status" in segment:
                                if segment["status"] == "cancelled":
                                    print(
                                        f"Task was cancelled: {segment.get('message', '')}"
                                    )
                                    break
                                elif segment["status"] == "error":
                                    self.error.emit(
                                        f"Server error: {segment.get('message', 'Unknown error')}"
                                    )
                                    break
                                continue

                            # Process normal segment
                            segment["start"] = round(segment.get("start", 0), 3)
                            segment["end"] = round(segment.get("end", 0), 3)
                            text = f"[{segment['start']} - {segment['end']}] {segment['text']}\n"

                            with self.lock:
                                with open(
                                    self.transcript_filename, "a", encoding="utf-8"
                                ) as f:
                                    f.write(text)
                                    f.flush()
                            if self.is_first_segment:
                                self.receive_first_segment.emit(
                                    "First Segment Received"
                                )
                                self.is_first_segment = False

                            self.progress.emit(text)
                        except json.JSONDecodeError:
                            print(f"Failed to decode JSON: {line}")
                        except Exception as e:
                            self.error.emit(f"Streaming decode error: {e}")

            if self._is_running:  # Only emit completion if not cancelled
                self.finished.emit("Transcription completed and saved.")

        except requests.exceptions.ConnectionError as e:
            self.error.emit(f"Connection error: {str(e)}. Is the server running?")
        except requests.exceptions.Timeout:
            self.error.emit("Request timed out. The server may be overloaded.")
        except Exception as e:
            self.error.emit(f"Request failed: {str(e)}")
        finally:
            # Clean up if the thread completes naturally (not via stop())
            self._cleanup()

    def stop(self):
        """Stop the transcription process and cleanup."""
        print("Stopping transcription worker...")
        self._is_running = False

        # Cancel the task on the server if we have a task_id
        if self.task_id:
            try:
                print(f"Sending cancellation request for task {self.task_id}...")
                cancel_response = requests.post(
                    f"http://localhost:{self.server_port}/cancel/{self.task_id}",
                    timeout=5,
                )
                if cancel_response.status_code == 200:
                    print(f"Task {self.task_id} cancellation initiated successfully")
                else:
                    print(f"Failed to cancel task: {cancel_response.text}")

                # Also send a cleanup request
                cleanup_response = requests.delete(
                    f"http://localhost:{self.server_port}/cleanup/{self.task_id}",
                    timeout=5,
                )
                if cleanup_response.status_code == 200:
                    print(f"Task {self.task_id} cleaned up successfully")
                else:
                    print(f"Failed to clean up task: {cleanup_response.text}")
            except Exception as e:
                print(f"Error during task cancellation: {e}")

        # Close the response object if it exists
        if hasattr(self, "response") and self.response:
            try:
                self.response.close()
            except Exception as e:
                print(f"Error closing response: {e}")

        # Wait for the thread to finish before declaring it stopped
        self.wait(timeout=5000)  # Wait up to 5 seconds
        print("Transcription worker stopped.")

    def _cleanup(self):
        """Internal method to clean up resources."""
        # Don't stop the server if we're not responsible for it
        # or if it might be reused for future requests
        if self.transcription_server and not getattr(
            self.transcription_server, "persistent", False
        ):
            self.transcription_server.stop()

        # Reset task_id
        self.task_id = None

        # Close response if still open
        if hasattr(self, "response") and self.response:
            try:
                self.response.close()
            except Exception:
                pass
