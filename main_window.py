from PySide6.QtWidgets import QMainWindow, QStackedWidget
from TranscriptionComponents.server import TranscriptionServer
from scene1 import Scene1
from scene2 import Scene2
from VideoPlayerLogic import VideoPlayerLogic


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
        self.scene1 = Scene1(self)
        self.scene2 = Scene2(self, self.transcription_server)
        self.video_player = VideoPlayerLogic(self)

        # Add scenes to the stacked widget
        self.stacked_widget.addWidget(self.scene1)
        self.stacked_widget.addWidget(self.scene2)
        self.stacked_widget.addWidget(self.video_player)

    def switch_to_scene1(self):
        """Switch to Scene1."""
        try:
            self.stacked_widget.setCurrentIndex(self.SCENE1_INDEX)
        except Exception as e:
            print(f"Error switching to Scene1: {e}")

    def switch_to_scene2(self, path, language):
        """Switch to Scene2 and start transcription."""
        try:
            self.scene2.reset_scene()
            self.scene2.transcript(path, language)
            self.stacked_widget.setCurrentIndex(self.SCENE2_INDEX)
        except Exception as e:
            print(f"Error switching to Scene2: {e}")

    def switch_to_video_player(self, path, language):
        """Switch to VideoPlayer and load the video."""
        try:
            self.video_player.load_video(path, language)
            self.stacked_widget.setCurrentIndex(self.VIDEO_PLAYER_INDEX)
        except Exception as e:
            print(f"Error switching to VideoPlayer: {e}")

    def get_current_scene_index(self):
        """Return the index of the currently displayed scene."""
        return self.stacked_widget.currentIndex()
