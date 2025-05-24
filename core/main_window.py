from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import QEvent
from ui.views.welcome_view import Welcome
from ui.views.upload_view import Upload
from core.VideoPlayerLogic import VideoPlayerLogic
from services.api.server import TranscriptionServer
from utils.logging_config import setup_logging


class MainWindow(QMainWindow):
    VIEW1_INDEX = 0
    VIEW2_INDEX = 1
    VIDEO_PLAYER_INDEX = 2

    def __init__(self):
        super().__init__()
        self.logger = setup_logging()
        self.transcription_server = TranscriptionServer()
        self.setWindowTitle("Video Player with Subtitles")
        self.resize(800, 600)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.welcome_view = Welcome(self)
        self.upload_view = Upload(self, self.transcription_server)
        self.video_player = VideoPlayerLogic(
            main_window=self,
            transcription_server=self.transcription_server,
        )
        self.stacked_widget.addWidget(self.welcome_view)
        self.stacked_widget.addWidget(self.upload_view)
        self.stacked_widget.addWidget(self.video_player)

    def closeEvent(self, event: QEvent):
        """Handle window close event to clean up resources."""
        try:
            if hasattr(self, "video_player"):
                self.video_player.media_player.stop()
                self.video_player.audio_output.setMuted(True)
                self.video_player.cancel_transcription()
            if hasattr(self, "transcription_server"):
                self.logger.info("Stopping transcription server")
                self.transcription_server.stop()
                self.logger.info("Transcription server stopped")
            event.accept()
        except Exception as e:
            self.logger.error("Error during cleanup: %s", str(e))
            event.accept()

    def switch_to_welcome_view(self):
        """Switch to Scene1."""
        try:
            self.stacked_widget.setCurrentIndex(self.VIEW1_INDEX)
            self.logger.info("Switched to Scene1")
        except Exception as e:
            self.logger.error("Error switching to Scene1: %s", str(e))

    def switch_to_upload_view(self, path, language):
        """Switch to Scene2 and start transcription."""
        try:
            self.upload_view.reset_scene()
            self.upload_view.transcript(path, language)
            self.stacked_widget.setCurrentIndex(self.VIEW2_INDEX)
            self.logger.info(
                "Switched to Scene2 with video: %s, language: %s", path, language
            )
        except Exception as e:
            self.logger.error("Error switching to Scene2: %s", str(e))

    def switch_to_video_player(self, path, language):
        """Switch to VideoPlayer and load the video."""
        try:
            self.video_player.task_id = self.upload_view.transcription_worker.task_id
            self.video_player.load_video(path, language)
            self.stacked_widget.setCurrentIndex(self.VIDEO_PLAYER_INDEX)
            self.logger.info(
                "Switched to VideoPlayer with video: %s, language: %s", path, language
            )
        except Exception as e:
            self.logger.error("Error switching to VideoPlayer: %s", str(e))
