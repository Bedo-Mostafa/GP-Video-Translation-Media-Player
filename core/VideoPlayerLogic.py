from PySide6.QtCore import Signal, QTimer
from ui.views.video_view import VideoPlayerUI
from core.MediaController import MediaController
from core.SubtitleManager import SubtitleManager
from utils.logging_config import setup_logging
from utils.config import get_transcript_file

class VideoPlayerLogic(VideoPlayerUI):
    switch_scene_signal = Signal(str)

    def __init__(self, main_window, transcription_server):
        super().__init__(main_window)
        self.logger = setup_logging()
        self.main_window = main_window
        self.transcription_server = transcription_server
        self.transcription_worker = None
        self.task_id = None
        self.src_lang = None
        self.tgt_lang = None
        self.timer = QTimer()
        self.media_controller = MediaController(
            self.media_player,
            self.audio_output,
            self.play_button,
            self.volume_button,
            self.volume_slider,
            self.progress_slider,
        )
        self.subtitle_manager = SubtitleManager(
            self.media_player,
            self.subtitle_text,
            self.updateSubtitlePosition,
            self.timer,
        )

        self._setup_connections()
        self.audio_output.setVolume(0.5)
        self.media_controller.update_volume_icon(50)
        self.timer.start(100)

    def _setup_connections(self):
        """Connect signals for scene switching and transcription cancellation."""
        self.rewind_button.clicked.connect(self.rewind_video)
        self.forward_button.clicked.connect(self.forward_video)
        self.cancel_button.clicked.connect(self.cancel_transcription)
        self.switch_scene_signal.connect(self.main_window.switch_to_welcome_view)
        self.media_player.positionChanged.connect(self.update_time_label)
        self.media_player.durationChanged.connect(self.update_time_label)

    def load_video(self, video_path):
        """Load video and initialize transcription."""
        self.logger.info(
            "Loading video player with video: %s, src_lang: %s, tgt_lang: %s", video_path, self.src_lang, self.tgt_lang
        )
        self.media_controller.load_video(video_path)
        # if(src_lang != tgt_lang): # If translation then save src as well
        #     self.subtitle_manager.load_initial_transcription(src_lang)
        self.subtitle_manager.load_initial_transcription(self.tgt_lang)
        QTimer.singleShot(100, self.updateSceneRect)
        QTimer.singleShot(500, self.updateSceneRect)
        if self.transcription_worker:
            self.transcription_worker.finished.connect(
                self.subtitle_manager.set_transcription_complete
            )

    def cancel_transcription(self):
        """Cancel transcription and switch to scene 1 after cleanup."""
        self.logger.info("Cancelling transcription and switching to scene 1")
        self.media_controller.stop()
        if self.transcription_worker:
            self.transcription_worker.stop()
            self.transcription_worker.wait()
            self.logger.info("Transcription worker stopped")
        self.task_id = None
        if self.transcription_server:
            self.transcription_server.cleanup()
            self.logger.info("Transcription server cleaned up")
        self.switch_scene_signal.emit("Cancelled")

    def rewind_video(self):
        """Rewind video by 5 seconds."""
        position = self.media_player.position()
        self.showBuffering(True)
        self.media_player.setPosition(max(0, position - 5000))
        self.showBuffering(False)
        self.logger.debug("Rewinded video by 5 seconds")

    def forward_video(self):
        """Fast forward video by 5 seconds."""
        position = self.media_player.position()
        duration = self.media_player.duration()
        self.showBuffering(True)
        self.media_player.setPosition(min(duration, position + 5000))
        self.showBuffering(False)
        self.logger.debug("Fast forwarded video by 5 seconds")

    def update_time_label(self):
        """Update the time label with current position and duration."""
        position_sec = self.media_player.position() // 1000
        duration_sec = self.media_player.duration() // 1000
        show_hours = duration_sec >= 3600
        time_format = lambda s: (
            f"{s // 3600:02}:{(s % 3600) // 60:02}:{s % 60:02}"
            if show_hours
            else f"{(s % 3600) // 60:02}:{s % 60:02}"
        )
        self.time_label.setText(
            f"{time_format(position_sec)} / {time_format(duration_sec)}"
        )
        self.logger.debug("Updated time label")

    def showBuffering(self, visible=True):
        """Show or hide the buffering indicator."""
        self.buffering_indicator.setVisible(visible)

    def is_buffering_visible(self):
        """Check if the buffering indicator is visible."""
        return self.buffering_indicator.isVisible()
