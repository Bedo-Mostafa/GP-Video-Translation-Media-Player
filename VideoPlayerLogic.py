import os
from PySide6.QtCore import Signal
import requests
import threading
from filelock import FileLock, Timeout
from views.video_view import VideoPlayerUI
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer


class VideoPlayerLogic(VideoPlayerUI):
    switch_scene_signal = Signal(str)

    def __init__(self, main_window, transcription_server=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.transcription_server = transcription_server
        self.update_counter = 0
        self.update_interval = 10
        self.manual_position_update = False
        self.transcript_segments = []
        self.task_id = None
        self.buffering_check_timer = QTimer()
        self.buffering_check_timer.setInterval(100)
        self.buffering_check_timer.timeout.connect(self.check_buffering_state)
        self.last_position = 0
        self.buffering_counter = 0
        self.waiting_for_subtitle = False

        # Connect signals
        self.rewind_button.clicked.connect(self.rewind_video)
        self.play_button.clicked.connect(self.toggle_play_pause)
        self.forward_button.clicked.connect(self.forward_video)
        self.progress_slider.sliderMoved.connect(self.set_video_position)
        self.volume_button.clicked.connect(self.toggle_volume_slider)
        self.volume_slider.valueChanged.connect(self.change_volume)

        self.cancel_button.clicked.connect(self.cancel_transcription)
        self.switch_scene_signal.connect(self.main_window.switch_to_scene1)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position_slider)
        self.timer.timeout.connect(self.check_subtitle)

        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.positionChanged.connect(self.update_time_label)
        self.media_player.durationChanged.connect(self.update_time_label)

        # Connect media player state changes to monitor buffering
        self.media_player.playbackStateChanged.connect(
            self.handle_playback_state_change
        )
        self.media_player.mediaStatusChanged.connect(self.handle_media_status_change)

        self.audio_output.setVolume(0.5)
        self.update_volume_icon(50)

    def handle_playback_state_change(self, state):
        """Handle changes in playback state to detect buffering"""
        if state == QMediaPlayer.PlayingState:
            # Start the buffering check timer when playing
            self.buffering_check_timer.start()
            # If we were showing buffering before, give it a moment to stabilize
            if self.buffering_indicator.isVisible():
                QTimer.singleShot(500, lambda: self.showBuffering(False))
        elif state == QMediaPlayer.PausedState:
            # Stop the buffering check when paused
            self.buffering_check_timer.stop()
            self.showBuffering(False)
        elif state == QMediaPlayer.StoppedState:
            # Stop the buffering check when stopped
            self.buffering_check_timer.stop()
            self.showBuffering(False)

    def handle_media_status_change(self, status):
        """Handle changes in media status to detect buffering"""
        if status == QMediaPlayer.LoadingMedia:
            # Show buffering during initial loading
            self.showBuffering(True)
        elif status == QMediaPlayer.BufferingMedia:
            # Show buffering during buffering state
            self.showBuffering(True)
        elif status == QMediaPlayer.BufferedMedia:
            # Hide buffering when fully buffered
            self.showBuffering(False)
        elif status == QMediaPlayer.EndOfMedia:
            # Hide buffering at end of media
            self.showBuffering(False)
        elif status == QMediaPlayer.InvalidMedia:
            # Hide buffering if media is invalid
            self.showBuffering(False)

    def check_buffering_state(self):
        """Detect buffering by checking if position is advancing"""
        current_position = self.media_player.position()

        # If position hasn't changed for a bit and we're supposed to be playing
        if (
            current_position == self.last_position
            and self.media_player.playbackState() == QMediaPlayer.PlayingState
        ):
            self.buffering_counter += 1
            if self.buffering_counter >= 3:  # After ~300ms of no movement
                self.showBuffering(True)
        else:
            # Position is advancing normally
            self.buffering_counter = 0
            if self.buffering_indicator.isVisible():
                self.showBuffering(False)

        self.last_position = current_position

    def cancel_transcription(self):
        self.media_player.stop()
        self.audio_output.setMuted(True)
        self.buffering_check_timer.stop()
        self.showBuffering(False)

        def safe_cancel():
            try:
                # Only cancel the specific task, not the entire server
                if self.task_id:
                    print(f"Cancelling task {self.task_id}...")
                    # Send cancellation request to server
                    response = requests.post(
                        f"http://localhost:8000/cancel/{self.task_id}", timeout=5
                    )
                    if response.status_code == 200:
                        print(
                            f"Task {self.task_id} cancellation initiated successfully"
                        )
                    else:
                        print(f"Failed to cancel task: {response.text}")

                    # Clean up resources on server
                    cleanup_response = requests.delete(
                        f"http://localhost:8000/cleanup/{self.task_id}", timeout=5
                    )
                    if cleanup_response.status_code == 200:
                        print(f"Task {self.task_id} cleaned up successfully")
                    else:
                        print(f"Failed to clean up task: {cleanup_response.text}")

                    # Reset task_id after cancellation
                    self.task_id = None

                # Stop the transcription worker thread if it exists
                if hasattr(self, "transcription_worker") and self.transcription_worker:
                    print("Stopping transcription worker...")
                    self.transcription_worker.stop()
                    self.transcription_worker.wait()  # Ensure thread is joined safely
                    print("Transcription worker stopped.")
            except Exception as e:
                print(f"Error during cancellation: {e}")
            finally:
                self.switch_scene_signal.emit("Cancelled")

        threading.Thread(target=safe_cancel, daemon=True).start()

    def toggle_volume_slider(self):
        self.volume_slider.setVisible(not self.volume_slider.isVisible())

    def update_volume_icon(self, volume):
        if volume == 0:
            self.volume_button.setText("🔇")
        elif volume < 50:
            self.volume_button.setText("🔉")
        else:
            self.volume_button.setText("🔊")

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100.0)
        self.update_volume_icon(value)

    def load_video(self, video_path, language):
        # Show buffering indicator during initial load
        self.showBuffering(True)

        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.audio_output.setMuted(False)
        self.media_player.play()
        self.timer.start(100)
        self.buffering_check_timer.start(100)
        self.play_button.setText("⏸️")
        self.transcript_segments = []

        # Schedule scene updates to ensure proper video sizing
        QTimer.singleShot(100, self.updateSceneRect)
        QTimer.singleShot(500, self.updateSceneRect)  # Additional delay for loading

        try:
            transcript_path = "transcription.txt"
            if os.path.exists(transcript_path):
                with open(transcript_path, "r", encoding="utf-8") as f:
                    transcription = f.read()
                    self.parse_transcription(transcription)
        except Exception as e:
            print(f"Error reading initial transcription: {e}")

    def parse_transcription(self, transcription):
        new_segments = []
        for line in transcription.strip().split("\n"):
            if line:
                try:
                    time_str, text = line.split("]", 1)
                    time_str = time_str[1:]
                    start_str, end_str = time_str.split("-")
                    start = float(start_str.strip())
                    end = float(end_str.strip())
                    new_segments.append(
                        {"start": start, "end": end, "text": text.strip()}
                    )
                except Exception as e:
                    print(f"Error parsing line: {line}")
                    continue

        if new_segments:
            self.transcript_segments = new_segments

    def check_subtitle(self):
        current_time = self.media_player.position() / 1000.0
        current_text = ""
        found_subtitle = False
        has_future_subtitles = False

        for segment in self.transcript_segments:
            if segment["start"] <= current_time <= segment["end"]:
                current_text = segment["text"]
                found_subtitle = True
                break
            elif segment["start"] > current_time:
                has_future_subtitles = True

        if found_subtitle:
            if self.subtitle_text.toPlainText() != current_text:
                self.subtitle_text.setPlainText(current_text)

                # Center align the text
                doc = self.subtitle_text.document()
                option = doc.defaultTextOption()
                option.setAlignment(Qt.AlignHCenter)
                doc.setDefaultTextOption(option)

                self.updateSubtitlePosition()

            # Resume playback if we were waiting for subtitle
            if self.waiting_for_subtitle:
                print("Subtitle found. Resuming playback.")
                self.media_player.play()
                self.play_button.setText("⏸️")
                self.waiting_for_subtitle = False
        else:
            # No subtitle found at current time, but continue playing if there are future subtitles
            if (
                self.media_player.playbackState() == QMediaPlayer.PlayingState
                and not self.waiting_for_subtitle
                and not has_future_subtitles
            ):
                print("No subtitle found and no future subtitles. Pausing playback.")
                self.media_player.pause()
                self.play_button.setText("⏯️")
                self.waiting_for_subtitle = True
            elif has_future_subtitles and self.waiting_for_subtitle:
                # Resume playback if we were waiting but found future subtitles
                print("Future subtitles found. Resuming playback.")
                self.media_player.play()
                self.play_button.setText("⏸️")
                self.waiting_for_subtitle = False

        self.update_counter += 1
        if self.update_counter >= self.update_interval:
            self.update_counter = 0
            self.refresh_transcription()

    def refresh_transcription(self):
        try:
            transcript_path = "transcription.txt"
            if not os.path.exists(transcript_path):
                return

            current_position = self.media_player.position()

            try:
                lock = FileLock(transcript_path + ".lock", timeout=0.5)
                with lock:
                    with open(transcript_path, "r", encoding="utf-8") as f:
                        transcription = f.read()
                        new_segments = []
                        for line in transcription.strip().split("\n"):
                            if line:
                                try:
                                    time_str, text = line.split("]", 1)
                                    time_str = time_str[1:]
                                    start_str, end_str = time_str.split("-")
                                    start = float(start_str.strip())
                                    end = float(end_str.strip())
                                    new_segments.append(
                                        {
                                            "start": start,
                                            "end": end,
                                            "text": text.strip(),
                                        }
                                    )
                                except Exception as e:
                                    print(f"Error parsing line: {line}")
                                    continue

                        if new_segments:
                            self.transcript_segments = new_segments
            except Timeout:
                print("Transcription file locked, will retry later")
                return

            if self.media_player.position() != current_position:
                self.manual_position_update = True
                self.media_player.setPosition(current_position)
                QTimer.singleShot(100, self._reset_position_flag)
        except Exception as e:
            print(f"Error refreshing transcription: {e}")

    def toggle_play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText("⏯️")
        else:
            self.media_player.play()
            self.play_button.setText("⏸️")

    def update_duration(self, duration):
        self.progress_slider.setRange(0, duration)

    def update_position(self, position):
        if (
            position == 0
            and self.media_player.playbackState() == QMediaPlayer.PlayingState
        ):
            print("Warning: Video position reset to 0 unexpectedly")
        if not self.manual_position_update:
            self.progress_slider.setValue(position)

    def update_position_slider(self):
        if not self.manual_position_update:
            self.progress_slider.setValue(self.media_player.position())

    @staticmethod
    def format_time(seconds, show_hours=False):
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if show_hours or hours > 0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        else:
            return f"{minutes:02}:{seconds:02}"

    def update_time_label(self):
        position_sec = self.media_player.position() // 1000
        duration_sec = self.media_player.duration() // 1000
        show_hours = duration_sec >= 3600

        self.time_label.setText(
            f"{self.format_time(position_sec, show_hours)} / {self.format_time(duration_sec, show_hours)}"
        )

    def set_video_position(self, position):
        self.manual_position_update = True
        self.media_player.setPosition(position)
        # Show buffering indicator when manually seeking
        self.showBuffering(True)
        QTimer.singleShot(100, self._reset_position_flag)

    def _reset_position_flag(self):
        self.manual_position_update = False

    def rewind_video(self):
        position = self.media_player.position()
        self.media_player.setPosition(max(0, position - 5000))
        # Show buffering indicator when seeking
        self.showBuffering(True)

    def forward_video(self):
        position = self.media_player.position()
        duration = self.media_player.duration()
        self.media_player.setPosition(min(duration, position + 5000))
        # Show buffering indicator when seeking
        self.showBuffering(True)
