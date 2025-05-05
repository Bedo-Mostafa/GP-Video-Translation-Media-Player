import os
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtCore import QTimer, QUrl
from filelock import FileLock, Timeout
from VideoPlayerUI import VideoPlayerUI


class VideoPlayerLogic(VideoPlayerUI):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.update_counter = 0
        self.update_interval = 10
        self.manual_position_update = False
        self.transcript_segments = []

        # Connect signals
        self.rewind_button.clicked.connect(self.rewind_video)
        self.play_button.clicked.connect(self.toggle_play_pause)
        self.forward_button.clicked.connect(self.forward_video)
        self.progress_slider.sliderMoved.connect(self.set_video_position)
        self.volume_button.clicked.connect(self.toggle_volume_slider)
        self.volume_slider.valueChanged.connect(self.change_volume)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position_slider)
        self.timer.timeout.connect(self.check_subtitle)

        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.positionChanged.connect(self.update_time_label)
        self.media_player.durationChanged.connect(self.update_time_label)

        self.audio_output.setVolume(0.5)
        self.update_volume_icon(50)

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
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.media_player.play()
        self.timer.start(100)
        self.play_button.setText("⏸️")
        self.transcript_segments = []

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
        for line in transcription.strip().split('\n'):
            if line:
                try:
                    time_str, text = line.split(']', 1)
                    time_str = time_str[1:]
                    start_str, end_str = time_str.split('-')
                    start = float(start_str.strip())
                    end = float(end_str.strip())
                    new_segments.append({
                        'start': start,
                        'end': end,
                        'text': text.strip()
                    })
                except Exception as e:
                    print(f"Error parsing line: {line}")
                    continue

        if new_segments:
            self.transcript_segments = new_segments

    def check_subtitle(self):
        current_time = self.media_player.position() / 1000.0
        current_text = ""
        for segment in self.transcript_segments:
            if segment['start'] <= current_time <= segment['end']:
                current_text = segment['text']
                break

        if self.subtitle_label.text() != current_text:
            self.subtitle_label.setText(current_text)

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
                        for line in transcription.strip().split('\n'):
                            if line:
                                try:
                                    time_str, text = line.split(']', 1)
                                    time_str = time_str[1:]
                                    start_str, end_str = time_str.split('-')
                                    start = float(start_str.strip())
                                    end = float(end_str.strip())
                                    new_segments.append({
                                        'start': start,
                                        'end': end,
                                        'text': text.strip()
                                    })
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
        if position == 0 and self.media_player.playbackState() == QMediaPlayer.PlayingState:
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
        QTimer.singleShot(100, self._reset_position_flag)

    def _reset_position_flag(self):
        self.manual_position_update = False

    def rewind_video(self):
        position = self.media_player.position()
        self.media_player.setPosition(max(0, position - 5000))

    def forward_video(self):
        position = self.media_player.position()
        duration = self.media_player.duration()
        self.media_player.setPosition(min(duration, position + 5000))
