from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QProgressBar,
    QLabel, QMessageBox, QSizePolicy
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt
from TranscriptionWorkerAPI import TranscriptionWorkerAPI


class Scene2(QWidget):
    def __init__(self, main_window,transcription_server, video_path=None, language=None):
        super().__init__()
        self.transcription_server = transcription_server
        self.main_window = main_window
        self.transcription_worker = None

        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Upload label
        self.upload_label = QLabel("Uploading video, please wait...")
        self.upload_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upload_label.setObjectName("UploadLabel")
        layout.addWidget(self.upload_label)

        # Web Engine View for SVG Animation
        self.webview = QWebEngineView()
        self.webview.setMinimumSize(400, 300)
        self.webview.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.Animation_layout = QHBoxLayout()
        self.Animation_layout.addWidget(self.webview)
        self.Animation_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.Animation_layout.setObjectName("Animation_layout")
        layout.addLayout(self.Animation_layout)

        # Load animation into HTML
        html_file = "animationLoader.html"
        with open(html_file, "r", encoding="utf-8") as file:
            html_template = file.read()
        self.webview.setHtml(html_template)

        # Styled progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setObjectName("progress_bar")
        layout.addWidget(self.progress_bar)

        # Back button
        button = QPushButton("Back")
        button.clicked.connect(self.stop_upload_and_back)
        button.setObjectName("CancelButton")
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def stop_upload_and_back(self):
        if self.transcription_worker:
            print("Stopping transcription worker...")
            self.transcription_worker.stop()
            self.transcription_worker.wait()
            print("Transcription worker stopped.")
            self.transcription_worker = None

        self.main_window.switch_to_scene1()

    def transcript(self, video_path, language):
        self.video_path = video_path
        self.language = language
        print(f"Starting transcription for: {video_path}")

        if not video_path:
            print("Error: No video file selected")
            return

        self.transcription_worker = TranscriptionWorkerAPI(
            video_path, self.language, self.transcription_server)
        self.transcription_worker.progress.connect(self.update_progress)
        self.transcription_worker.receive_first_segment.connect(
            self.handle_transcription)
        self.transcription_worker.error.connect(self.handle_error)
        self.transcription_worker.start()
        print("TranscriptionWorker started")

    def handle_transcription(self):
        print("Received transcription")
        self.main_window.switch_to_video_player(self.video_path, self.language)

    def handle_error(self, error_message):
        print(f"Error received: {error_message}")
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Error")
        msg_box.setIcon(QMessageBox.Critical)

        if "internet" in error_message.lower():
            msg_box.setText(
                "Internet is not turned on. Please check your connection and try again.")
        else:
            msg_box.setText(f"An error occurred: {error_message}")

        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    def update_progress(self, message):
        print(f"Progress update: {message}")
        if message.startswith("Uploading:"):
            percent = int(message.split(":")[1].replace("%", "").strip())
            if percent < 4:
                self.progress_bar.setValue(0)
            else:
                if percent == 100:
                    self.upload_label.setText(
                        "Processing video, please wait...")
                self.progress_bar.setValue(percent)
        else:
            current = self.progress_bar.value()
            self.progress_bar.setValue(min(100, current + 1))

    def reset_scene(self):
        self.upload_label.setText("Uploading video, please wait...")
        self.progress_bar.setValue(0)

        html_file = "animationLoader.html"
        with open(html_file, "r", encoding="utf-8") as file:
            html_template = file.read()
        self.webview.setHtml(html_template)
