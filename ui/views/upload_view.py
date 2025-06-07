from os import path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QLabel,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt
from core import main_window
from services.TranscriptionWorkerAPI import TranscriptionWorkerAPI
from utils.logging_config import setup_logging


class Upload(QWidget):
    def __init__(
        self,
        main_window: main_window,
        transcription_server,
        video_path=None,
        src_lang=None,
        tgt_lang=None, 
    ):
        super().__init__()
        self.logger = setup_logging()
        self.transcription_server = transcription_server
        self.main_window = main_window
        self.transcription_worker = None
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upload_label = QLabel("Uploading video, please wait...")
        self.upload_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upload_label.setObjectName("UploadLabel")
        self.layout.addWidget(self.upload_label)
        self.webview = QWebEngineView()
        self.webview.setMinimumSize(400, 300)
        self.webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        Animation_layout = QHBoxLayout()
        Animation_layout.addWidget(self.webview)
        Animation_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        Animation_layout.setObjectName("Animation_layout")

        self.layout.addLayout(Animation_layout)

        path_to_animation_html = path.join("ui//assets", "animationLoader.html")
        self.file_html = path_to_animation_html

        with open(self.file_html, "r", encoding="utf-8") as file:
            self.webview.setHtml(file.read())

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setObjectName("progress_bar")
        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)

    def transcript(self, video_path, src_lang, tgt_lang):
        """Start transcription for the given video."""
        self.video_path = video_path
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        
        self.logger.info(
            "Starting transcription for video: %s, src_lang: %s, tgt_lang: %s", video_path, src_lang, tgt_lang
        )
        if not video_path:
            self.logger.error("No video file selected")
            return
        self.transcription_worker = TranscriptionWorkerAPI(
            video_path, src_lang, tgt_lang, self.transcription_server
        )
        self.main_window.video_player.transcription_worker = self.transcription_worker
        self.transcription_worker.progress.connect(self.update_progress)
        self.transcription_worker.receive_first_segment.connect(
            self.handle_transcription
        )
        self.transcription_worker.finished.connect(
            self.main_window.video_player.subtitle_manager.set_transcription_complete
        )
        self.transcription_worker.error.connect(self.handle_error)
        self.transcription_worker.start()
        self.logger.info("TranscriptionWorker started")

    def handle_transcription(self):
        """Handle completion of first transcription segment."""
        self.logger.info("Received first transcription segment")
        self.main_window.switch_to_video_player(self.video_path, self.src_lang, self.tgt_lang)

    def handle_error(self, error_message):
        """Display error message to the user."""
        self.logger.error("Transcription error: %s", error_message)
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Error")
        msg_box.setIcon(QMessageBox.Critical)
        if "internet" in error_message.lower():
            msg_box.setText(
                "Internet is not turned on. Please check your connection and try again."
            )
        else:
            msg_box.setText(f"An error occurred: {error_message}")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    def update_progress(self, message):
        """Update progress bar based on transcription progress."""
        self.logger.debug("Progress update: %s", message)
        if message.startswith("Uploading:"):
            percent = int(message.split(":")[1].replace("%", "").strip())
            if percent < 4:
                self.progress_bar.setValue(0)
            else:
                if percent == 100:
                    self.upload_label.setText("Processing video, please wait...")
                self.progress_bar.setValue(percent)
        else:
            current = self.progress_bar.value()
            self.progress_bar.setValue(min(100, current + 1))

    def reset_scene(self):
        """Reset the upload scene to initial state."""
        self.upload_label.setText("Uploading video, please wait...")
        self.progress_bar.setValue(0)

        with open(self.file_html, "r", encoding="utf-8") as file:
            self.webview.setHtml(file.read())
