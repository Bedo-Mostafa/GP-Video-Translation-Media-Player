# import sys
# from PySide6.QtWidgets import (
#     QApplication,
#     QMainWindow,
#     QWidget,
#     QVBoxLayout,
#     QPushButton,
#     QFileDialog,
#     QGraphicsView,
#     QGraphicsScene,
# )
# from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
# from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
# from PySide6.QtCore import Qt, QUrl
# from PySide6.QtGui import QFont
# from PySide6.QtWidgets import QGraphicsTextItem


# class MediaPlayer(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("PySide6 Media Player with Static Subtitle")
#         self.setGeometry(100, 100, 800, 600)

#         # Initialize media player components
#         self.player = QMediaPlayer()
#         self.audio_output = QAudioOutput()
#         self.player.setAudioOutput(self.audio_output)

#         # Create graphics view for video and static text
#         self.scene = QGraphicsScene()
#         self.graphics_view = QGraphicsView(self.scene)
#         self.video_item = QGraphicsVideoItem()
#         self.scene.addItem(self.video_item)
#         self.player.setVideoOutput(self.video_item)

#         # Static text item (replacing subtitle)
#         self.subtitle_item = QGraphicsTextItem()
#         self.subtitle_item.setFont(QFont("Arial", 16))
#         self.subtitle_item.setDefaultTextColor(Qt.white)
#         self.subtitle_item.setTextWidth(700)
#         self.subtitle_item.setPos(50, 400)  # Position at bottom
#         self.subtitle_item.setPlainText("Sample Subtitle Text")  # Static text
#         self.scene.addItem(self.subtitle_item)

#         # Main widget and layout
#         self.central_widget = QWidget()
#         self.setCentralWidget(self.central_widget)
#         self.layout = QVBoxLayout(self.central_widget)
#         self.layout.addWidget(self.graphics_view)

#         # Control buttons
#         self.play_button = QPushButton("Play")
#         self.play_button.clicked.connect(self.toggle_play)
#         self.layout.addWidget(self.play_button)

#         self.load_video_button = QPushButton("Load Video")
#         self.load_video_button.clicked.connect(self.load_video)
#         self.layout.addWidget(self.load_video_button)

#         # Connect player signals
#         self.player.positionChanged.connect(self.on_position_changed)

#     def toggle_play(self):
#         if self.player.playbackState() == QMediaPlayer.PlayingState:
#             self.player.pause()
#             self.play_button.setText("Play")
#         else:
#             self.player.play()
#             self.play_button.setText("Pause")

#     def load_video(self):
#         file_name, _ = QFileDialog.getOpenFileName(
#             self, "Open Video File", "", "Videos (*.mp4 *.avi *.mkv)"
#         )
#         if file_name:
#             self.player.setSource(QUrl.fromLocalFile(file_name))
#             self.video_item.setSize(self.graphics_view.size())
#             self.player.play()
#             self.play_button.setText("Pause")

#     def on_position_changed(self, position):
#         self.video_item.setSize(self.graphics_view.size())  # Resize video to fit


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     player = MediaPlayer()
#     player.show()
#     sys.exit(app.exec())

# # import sys
# # import os
# # from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
# # from PySide6.QtMultimediaWidgets import QVideoWidget
# # from PySide6.QtWidgets import (
# #     QApplication,
# #     QMainWindow,
# #     QVBoxLayout,
# #     QPushButton,
# #     QWidget,
# #     QSlider,
# #     QHBoxLayout,
# #     QSizePolicy,
# #     QLabel,
# # )
# # from PySide6.QtCore import Qt, QUrl


# # class VideoPlayerUI(QMainWindow):
# #     def __init__(self, main_window):
# #         super().__init__()
# #         self.main_window = main_window
# #         self.resize(800, 600)

# #         # Create central widget and layout
# #         central_widget = QWidget()
# #         central_widget.setObjectName("central_widget")
# #         self.setCentralWidget(central_widget)
# #         layout = QVBoxLayout(central_widget)

# #         # Create a container widget for video and subtitles
# #         video_container = QWidget()
# #         video_container.setObjectName("video_container")
# #         video_layout = QVBoxLayout(video_container)
# #         video_layout.setContentsMargins(0, 0, 0, 0)

# #         # Video widget
# #         self.video_widget = QVideoWidget()
# #         self.video_widget.setObjectName("video_widget")
# #         self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

# #         # Subtitle label
# #         self.subtitle_label = QLabel("Sample Subtitle Text")
# #         self.subtitle_label.setObjectName("subtitle_label")
# #         self.subtitle_label.setAlignment(Qt.AlignCenter)
# #         self.subtitle_label.setWordWrap(True)
# #         self.subtitle_label.setAttribute(
# #             Qt.WA_TransparentForMouseEvents
# #         )  # Allow clicks to pass through
# #         self.subtitle_label.setStyleSheet(
# #             """
# #             QLabel {
# #                 color: white;
# #                 font-size: 16px;
# #                 background-color: rgba(0, 0, 0, 0.5);  /* Semi-transparent black background */
# #                 padding: 5px;
# #             }
# #         """
# #         )

# #         # Overlay widget to hold video and subtitle
# #         overlay_widget = QWidget()
# #         overlay_layout = QVBoxLayout(overlay_widget)
# #         overlay_layout.setContentsMargins(0, 0, 0, 0)
# #         overlay_layout.addWidget(self.video_widget)
# #         overlay_layout.addWidget(self.subtitle_label, alignment=Qt.AlignBottom)

# #         video_layout.addWidget(overlay_widget)
# #         layout.addWidget(video_container)

# #         # Media player setup
# #         self.media_player = QMediaPlayer()
# #         self.audio_output = QAudioOutput()
# #         self.media_player.setAudioOutput(self.audio_output)
# #         self.media_player.setVideoOutput(self.video_widget)

# #         # Load and play the video
# #         video_path = (
# #             "TestVideo.mp4"  # Assumes file is in the same directory as the script
# #         )
# #         if os.path.exists(video_path):
# #             self.media_player.setSource(QUrl.fromLocalFile(os.path.abspath(video_path)))
# #             self.media_player.play()
# #         else:
# #             self.subtitle_label.setText("Error: TestVideo.mp4 not found")

# #         # Control bar
# #         control_bar = QWidget()
# #         control_bar.setObjectName("control_bar")
# #         control_layout = QHBoxLayout(control_bar)
# #         control_layout.setContentsMargins(5, 5, 5, 5)
# #         control_layout.setSpacing(5)

# #         # Rewind button (⏪)
# #         self.rewind_button = QPushButton("⏪")
# #         self.rewind_button.setObjectName("rewind_button")
# #         self.rewind_button.setFixedSize(30, 30)
# #         control_layout.addWidget(self.rewind_button)

# #         # Play/Pause button
# #         self.play_button = QPushButton("⏯️")
# #         self.play_button.setObjectName("play_button")
# #         self.play_button.setFixedSize(30, 30)
# #         self.play_button.clicked.connect(self.toggle_play)
# #         control_layout.addWidget(self.play_button)
# #         if os.path.exists(video_path):
# #             self.play_button.setText(
# #                 "⏸️"
# #             )  # Set to pause symbol since video starts playing

# #         # Fast Forward button (⏩)
# #         self.forward_button = QPushButton("⏩")
# #         self.forward_button.setObjectName("forward_button")
# #         self.forward_button.setFixedSize(30, 30)
# #         control_layout.addWidget(self.forward_button)

# #         # Progress slider
# #         self.progress_slider = QSlider(Qt.Horizontal)
# #         self.progress_slider.setObjectName("progress_slider")
# #         self.progress_slider.setMinimum(0)
# #         self.progress_slider.setMaximum(1000)  # Default range, will be updated
# #         self.progress_slider.setValue(0)
# #         control_layout.addWidget(self.progress_slider)

# #         # Time label
# #         self.time_label = QLabel("00:00 / 00:00")
# #         self.time_label.setObjectName("time_label")
# #         self.time_label.setFixedHeight(30)
# #         control_layout.addWidget(self.time_label)

# #         # Add Cancel button to the control bar
# #         self.cancel_button = QPushButton("🏠")
# #         self.cancel_button.setObjectName("cancel_button")
# #         self.cancel_button.setFixedSize(30, 30)
# #         control_layout.addWidget(self.cancel_button)

# #         # Volume button (toggles volume slider)
# #         self.volume_button = QPushButton("🔊")
# #         self.volume_button.setObjectName("volume_button")
# #         self.volume_button.setFixedSize(30, 30)
# #         control_layout.addWidget(self.volume_button)

# #         # Volume slider (hidden by default)
# #         self.volume_slider = QSlider(Qt.Horizontal)
# #         self.volume_slider.setObjectName("volume_slider")
# #         self.volume_slider.setRange(0, 100)
# #         self.volume_slider.setValue(50)  # Default volume at 50%
# #         # PolicingPolicyControlLayout.addWidget(self.volume_slider)
# #         self.volume_slider.setFixedWidth(100)
# #         self.volume_slider.setVisible(False)  # Hidden initially
# #         control_layout.addWidget(self.volume_slider)

# #         layout.addWidget(control_bar)

# #     def toggle_play(self):
# #         if self.media_player.playbackState() == QMediaPlayer.PlayingState:
# #             self.media_player.pause()
# #             self.play_button.setText("⏯️")
# #         else:
# #             self.media_player.play()
# #             self.play_button.setText("⏸️")


# # if __name__ == "__main__":
# #     app = QApplication(sys.argv)
# #     main_window = QWidget()  # Dummy main window for testing
# #     player = VideoPlayerUI(main_window)
# #     player.show()
# #     sys.exit(app.exec())




from faster_whisper import WhisperModel
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

model_size = "small"

model = WhisperModel(model_size, device="cuda", compute_type="int8")
# segments, info = model.transcribe("audio.mp3", beam_size=5, language="en", condition_on_previous_text=False)

# for segment in segments:
#     print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
# Load a test audio file
# audio, sample_rate = sf.read("test_audio.wav")  # Use a known good WAV file
segments, _ = model.transcribe("test_audio.wav", word_timestamps=True)

for segment in segments:
    for word in segment.words:
        print("[%.2fs -> %.2fs] %s" % (word.start, word.end, word.word))