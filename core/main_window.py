from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import QEvent
from ui.views.welcome_view import Welcome
from ui.views.upload_view import Upload
from core.VideoPlayerLogic import VideoPlayerLogic
from services.api.server import TranscriptionServer
from utils.logging_config import setup_logging


class MainWindow(QMainWindow):
    SCENE1_INDEX = 0
    SCENE2_INDEX = 1
    VIDEO_PLAYER_INDEX = 2

    def __init__(self):
        super().__init__()
        self.logger = setup_logging()
        self.transcription_server = TranscriptionServer()
        self.setWindowTitle("Video Player with Subtitles")
        self.resize(800, 600)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.scene1 = Welcome(self)
        self.scene2 = Upload(self, self.transcription_server)
        self.video_player = VideoPlayerLogic(
            self, transcription_server=self.transcription_server
        )
        self.stacked_widget.addWidget(self.scene1)
        self.stacked_widget.addWidget(self.scene2)
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

    def switch_to_scene1(self):
        """Switch to Scene1."""
        try:
            self.stacked_widget.setCurrentIndex(self.SCENE1_INDEX)
            self.logger.info("Switched to Scene1")
        except Exception as e:
            self.logger.error("Error switching to Scene1: %s", str(e))

    def switch_to_scene2(self, path, language):
        """Switch to Scene2 and start transcription."""
        try:
            self.scene2.reset_scene()
            self.scene2.transcript(path, language)
            self.stacked_widget.setCurrentIndex(self.SCENE2_INDEX)
            self.logger.info(
                "Switched to Scene2 with video: %s, language: %s", path, language
            )
        except Exception as e:
            self.logger.error("Error switching to Scene2: %s", str(e))

    def switch_to_video_player(self, path, language):
        """Switch to VideoPlayer and load the video."""
        try:
            self.video_player.task_id = self.scene2.transcription_worker.task_id
            self.video_player.load_video(path, language)
            self.stacked_widget.setCurrentIndex(self.VIDEO_PLAYER_INDEX)
            self.logger.info(
                "Switched to VideoPlayer with video: %s, language: %s", path, language
            )
        except Exception as e:
            self.logger.error("Error switching to VideoPlayer: %s", str(e))

    def get_current_scene_index(self):
        """Return the index of the currently displayed scene."""
        return self.stacked_widget.currentIndex()
