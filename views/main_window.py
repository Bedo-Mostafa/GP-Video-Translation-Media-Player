from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import QEvent
# from TranscriptionComponents.server import TranscriptionServer
from views.welcome_view import Welcome
from views.upload_view import Upload
from VideoPlayerLogic import VideoPlayerLogic
from transcription_service.api.server import TranscriptionServer


class MainWindow(QMainWindow):
    # Scene indices for clarity
    SCENE1_INDEX = 0
    SCENE2_INDEX = 1
    VIDEO_PLAYER_INDEX = 2

    def __init__(self):
        super().__init__()
        self.transcription_server = TranscriptionServer()

        # Initialize window properties
        self.setWindowTitle("Video Player with Subtitles")
        self.resize(800, 600)

        # Set up the stacked widget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Initialize scenes
        self.scene1 = Welcome(self)
        self.scene2 = Upload(self, self.transcription_server)
        self.video_player = VideoPlayerLogic(
            self, transcription_server=self.transcription_server)

        # Add scenes to the stacked widget
        self.stacked_widget.addWidget(self.scene1)
        self.stacked_widget.addWidget(self.scene2)
        self.stacked_widget.addWidget(self.video_player)

    def closeEvent(self, event: QEvent):
        """Handle window close event to clean up resources."""
        try:
            # Stop and clean up video player
            if hasattr(self, 'video_player'):
                self.video_player.media_player.stop()
                self.video_player.audio_output.setMuted(True)
                self.video_player.buffering_check_timer.stop()
                self.video_player.timer.stop()
                
                # Cancel any ongoing transcription
                if hasattr(self.video_player, 'cancel_transcription'):
                    self.video_player.cancel_transcription()

            # Stop transcription server
            if hasattr(self, 'transcription_server'):
                print("Stopping transcription server...")
                self.transcription_server.stop()
                print("Transcription server stopped.")

            # Accept the close event
            event.accept()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            # Still accept the close event even if cleanup fails
            event.accept()

    def switch_to_scene1(self):
        """Switch to Scene1."""
        try:
            self.stacked_widget.setCurrentIndex(self.SCENE1_INDEX)
        except Exception as e:
            print(f"Error switching to Scene1: {e}")

    def switch_to_scene2(self, path, language):
        """Switch to Scene2 and start transcription."""
        try:
            # self.video_player.task_id = self.scene2.transcription_worker.task_id
            self.scene2.reset_scene()
            self.scene2.transcript(path, language)
            self.stacked_widget.setCurrentIndex(self.SCENE2_INDEX)
        except Exception as e:
            print(f"Error switching to Scene2: {e}")

    def switch_to_video_player(self, path, language):
        """Switch to VideoPlayer and load the video."""
        try:
            # dynamically fetch the task ID
            self.video_player.task_id = self.scene2.transcription_worker.task_id
            self.video_player.load_video(path, language)
            self.stacked_widget.setCurrentIndex(self.VIDEO_PLAYER_INDEX)
        except Exception as e:
            print(f"Error switching to VideoPlayer: {e}")

    def get_current_scene_index(self):
        """Return the index of the currently displayed scene."""
        return self.stacked_widget.currentIndex()
