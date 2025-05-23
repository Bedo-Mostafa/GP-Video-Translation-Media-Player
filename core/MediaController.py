from PySide6.QtCore import QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from utils.config import BUFFERING_CHECK_INTERVAL
from utils.logging_config import setup_logging


class MediaController:
    """Manages media playback and audio controls."""

    def __init__(
        self,
        media_player,
        audio_output,
        play_button,
        volume_button,
        volume_slider,
        progress_slider,
    ):
        self.logger = setup_logging()
        self.media_player = media_player
        self.audio_output = audio_output
        self.play_button = play_button
        self.volume_button = volume_button
        self.volume_slider = volume_slider
        self.progress_slider = progress_slider
        self.buffering_check_timer = QTimer()
        self.buffering_check_timer.setInterval(BUFFERING_CHECK_INTERVAL)
        self.last_position = 0
        self.buffering_counter = 0
        self.manual_position_update = False
        self._setup_connections()

    def _setup_connections(self):
        """Connect signals for media control."""
        self.play_button.clicked.connect(self.toggle_play_pause)
        self.volume_button.clicked.connect(self.toggle_volume_slider)
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.progress_slider.sliderMoved.connect(self.set_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.positionChanged.connect(self.update_position)
        self.buffering_check_timer.timeout.connect(self.check_buffering)
        self.media_player.playbackStateChanged.connect(self.handle_playback_state)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)

    def load_video(self, video_path):
        """Load and play a video file."""
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.audio_output.setMuted(False)
        self.media_player.play()
        self.play_button.setText("⏸️")
        self.buffering_check_timer.start()

    def toggle_play_pause(self):
        """Toggle between play and pause states."""
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText("⏯️")
            self.logger.info("Video paused")
        else:
            self.media_player.play()
            self.play_button.setText("⏸️")
            self.logger.info("Video playing")

    def change_volume(self, value):
        """Update volume and volume icon."""
        self.audio_output.setVolume(value / 100.0)
        self.update_volume_icon(value)

    def update_volume_icon(self, volume):
        """Update the volume button icon based on volume level."""
        if volume == 0:
            self.volume_button.setText("🔇")
        elif volume < 50:
            self.volume_button.setText("🔉")
        else:
            self.volume_button.setText("🔊")

    def toggle_volume_slider(self):
        """Show or hide the volume slider."""
        self.volume_slider.setVisible(not self.volume_slider.isVisible())

    def set_position(self, position):
        """Set the video position and flag manual update."""
        self.manual_position_update = True
        self.media_player.setPosition(position)
        QTimer.singleShot(100, self._reset_position_flag)

    def _reset_position_flag(self):
        """Reset the manual position update flag."""
        self.manual_position_update = False

    def update_duration(self, duration):
        """Update the progress slider range based on video duration."""
        self.progress_slider.setRange(0, duration)

    def update_position(self, position):
        """Update the progress slider position."""
        if not self.manual_position_update:
            self.progress_slider.setValue(position)
            self.logger.debug("Updated position to %d ms", position)
        if (
            position == 0
            and self.media_player.playbackState() == QMediaPlayer.PlayingState
        ):
            self.logger.warning("Video position reset to 0 unexpectedly")

    def check_buffering(self):
        """Check if the video is buffering."""
        current_position = self.media_player.position()
        if (
            current_position == self.last_position
            and self.media_player.playbackState() == QMediaPlayer.PlayingState
        ):
            self.buffering_counter += 1
            if self.buffering_counter >= 3:
                self._showBuffering(True)
        else:
            self.buffering_counter = 0
            self._showBuffering(False)
        self.last_position = current_position

    def handle_playback_state(self, state):
        """Handle playback state changes."""
        if state == QMediaPlayer.PlayingState:
            self.buffering_check_timer.start()
            if self._is_buffering_visible():
                QTimer.singleShot(500, lambda: self._showBuffering(False))
        elif state == QMediaPlayer.PausedState:
            self.buffering_check_timer.stop()
            self._showBuffering(False)
        elif state == QMediaPlayer.StoppedState:
            self.buffering_check_timer.stop()
            self._showBuffering(False)

    def handle_media_status(self, status):
        """Handle media status changes."""
        status_map = {
            QMediaPlayer.LoadingMedia: "Loading",
            QMediaPlayer.BufferingMedia: "Buffering",
            QMediaPlayer.BufferedMedia: "Buffered",
            QMediaPlayer.EndOfMedia: "End of Media",
            QMediaPlayer.InvalidMedia: "Invalid Media",
        }
        if status in status_map:
            self._showBuffering(
                status in [QMediaPlayer.LoadingMedia, QMediaPlayer.BufferingMedia]
            )

    def _showBuffering(self, visible=True):
        """Show or hide the buffering indicator."""

    def _is_buffering_visible(self):
        """Check if the buffering indicator is visible."""

    def stop(self):
        """Stop media playback and cleanup."""
        self.media_player.stop()
        self.audio_output.setMuted(True)
        self.buffering_check_timer.stop()
        self._showBuffering(False)
