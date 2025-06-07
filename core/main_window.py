from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import QEvent
from ui.views.welcome_view import Welcome
from ui.views.upload_view import Upload
from core.VideoPlayerLogic import VideoPlayerLogic
from services.api.server import TranscriptionServer
from utils.logging_config import setup_logging


class MainWindow(QMainWindow):
    views = ["view1", "view2", "video_player"]

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
            self.stacked_widget.setCurrentIndex(self.views.index("view1"))
            self.logger.info("Switched to Scene1")
        except Exception as e:
            self.logger.error("Error switching to Scene1: %s", str(e))

    def switch_to_upload_view(self, path, src_lang, tgt_lang):
        """Switch to Scene2 and start transcription."""
        try:
            self.upload_view.reset_scene()
            self.upload_view.transcript(path, src_lang, tgt_lang)
            self.stacked_widget.setCurrentIndex(self.views.index("view2"))
            self.logger.info(
                "Switched to Scene2 with video: %s, src_lang: %s, tgt_lang: %s",
                path,
                src_lang,
                tgt_lang,
            )
        except Exception as e:
            self.logger.error("Error switching to Scene2: %s", str(e))

    def switch_to_video_player(self, path, src_lang, tgt_lang):
        """Switch to VideoPlayer and load the video."""
        try:
            self.video_player.task_id = self.upload_view.transcription_worker.task_id
            self.video_player.src_lang = src_lang
            self.video_player.tgt_lang = tgt_lang
            self.video_player.load_video(path)
            self.stacked_widget.setCurrentIndex(self.views.index("video_player"))
            self.logger.info(
                "Switched to VideoPlayer with video: %s, src_lang: %s, tgt_lang: %s",
                path,
                src_lang,
                tgt_lang,
            )
        except Exception as e:
            self.logger.error("Error switching to VideoPlayer: %s", str(e))
