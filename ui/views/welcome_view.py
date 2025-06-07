from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
    QTextEdit,
    QSizePolicy,
    QComboBox
)
from PySide6.QtGui import QFont, QPixmap, QImage
from PySide6.QtCore import Qt, QTimer

from cv2 import VideoCapture, cvtColor, COLOR_BGR2RGB

LANG_CODE_MAP = {
    "English": "en",
    "Arabic": "ar",
    "Spanish": "es",
    "French": "fr",
    "German": "de"
}

class Welcome(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.video_path = None
        self.src_lang = "English"
        self.tgt_lang = "Arabic"

        # Main layout
        main_layout = QVBoxLayout(self)

        # Title
        title = QLabel("Auto Subtitle Generator")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Language Selection
        
        lang_layout = QHBoxLayout()
        languages = ["English", "Arabic", "Spanish", "French", "German"]
        self.src_lang_combo = QComboBox()
        self.src_lang_combo.addItems(languages)
        self.src_lang_combo.setCurrentText("English")

        self.tgt_lang_combo = QComboBox()
        self.tgt_lang_combo.addItems(languages)
        self.tgt_lang_combo.setCurrentText("Arabic")

        lang_layout.addWidget(QLabel("From:"))
        lang_layout.addWidget(self.src_lang_combo)
        lang_layout.addSpacing(20)
        lang_layout.addWidget(QLabel("To:"))
        lang_layout.addWidget(self.tgt_lang_combo)

        lang_layout.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(lang_layout)

        # Warning label for language selection
        self.language_warning = QLabel("⚠ Please select a language!")
        self.language_warning.setAlignment(Qt.AlignCenter)
        self.language_warning.setFixedHeight(50)  # Prevent layout jump
        self.language_warning.setVisible(False)
        self.language_warning.setObjectName("warning")

        main_layout.addWidget(self.language_warning)

        # Add Media Button
        self.media_button = QPushButton("📁 Add Media")
        self.media_button.clicked.connect(self.upload_video)
        self.media_button.setObjectName("Add_Media_Button")
        self.media_button.setFixedHeight(40)
        self.media_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(self.media_button)

        # File path display
        self.file_path_display = QTextEdit()
        self.file_path_display.setReadOnly(True)
        self.file_path_display.setFixedHeight(40)
        self.file_path_display.setPlaceholderText("No video selected...")
        main_layout.addWidget(self.file_path_display)

        # Thumbnail label
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedHeight(180)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setVisible(False)  # Hide it initially
        main_layout.addWidget(self.thumbnail_label)

        # Start button
        self.start_button = QPushButton("▶ Start Transcription")
        self.start_button.setObjectName("Start_button")
        self.start_button.setFixedHeight(50)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.send_data)
        main_layout.addWidget(self.start_button)

    def upload_video(self):
        file_dialog = QFileDialog()
        video_path, _ = file_dialog.getOpenFileName(
            self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mov)"
        )
        if video_path:
            self.video_path = video_path
            self.file_path_display.clear()
            self.file_path_display.setText(video_path)
            self.start_button.setEnabled(True)
            self.display_thumbnail(video_path)
        else:
            # Reset UI if no file is selected
            self.thumbnail_label.clear()
            self.file_path_display.clear()
            self.thumbnail_label.setVisible(False)
            self.start_button.setEnabled(False)

    def display_thumbnail(self, video_path):
        cap = VideoCapture(video_path)
        success, frame = cap.read()
        cap.release()
        if success:
            frame = cvtColor(frame, COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image).scaled(
                320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(pixmap)
            self.thumbnail_label.setVisible(True)
        else:
            self.thumbnail_label.clear()
            self.thumbnail_label.setVisible(False)

    def send_data(self):
        if self.video_path:
            self.src_lang = LANG_CODE_MAP[self.src_lang_combo.currentText()]
            self.tgt_lang = LANG_CODE_MAP[self.tgt_lang_combo.currentText()]
            self.main_window.switch_to_upload_view(self.video_path, self.src_lang, self.tgt_lang)
        else:
            # Show warning message for 3 seconds
            self.language_warning.setVisible(True)
            QTimer.singleShot(3000, lambda: self.language_warning.setVisible(False))
