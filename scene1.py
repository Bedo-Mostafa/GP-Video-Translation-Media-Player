from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog,
    QRadioButton, QTextEdit, QSizePolicy, QButtonGroup
)
from PySide6.QtGui import QFont, QPixmap, QImage
from PySide6.QtCore import Qt, QTimer
import cv2


class Scene1(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.video_path = None
        self.is_arabic = None  # True for Arabic, False for English

        # Main layout
        main_layout = QVBoxLayout(self)

        # Title
        title = QLabel("Auto Subtitle Generator")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Language Selection
        lang_layout = QHBoxLayout()
        self.arabic_rb = QRadioButton("Arabic")
        self.english_rb = QRadioButton("English")

        self.lang_group = QButtonGroup(self)
        self.lang_group.setExclusive(True)
        self.lang_group.addButton(self.arabic_rb)
        self.lang_group.addButton(self.english_rb)

        for rb in (self.arabic_rb, self.english_rb):
            rb.setFixedSize(120, 60)
            rb.toggled.connect(self.set_language_selection)
            lang_layout.addWidget(rb)

        lang_layout.setSpacing(50)
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
        self.media_button.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        cap.release()
        if success:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            image = QImage(frame.data, w, h, bytes_per_line,
                           QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image).scaled(
                320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(pixmap)
            self.thumbnail_label.setVisible(True)
        else:
            self.thumbnail_label.clear()
            self.thumbnail_label.setVisible(False)

    def set_language_selection(self):
        if self.arabic_rb.isChecked():
            self.is_arabic = True
        elif self.english_rb.isChecked():
            self.is_arabic = False

    def send_data(self):
        if self.video_path is not None and self.lang_group.checkedButton() is not None:
            self.main_window.switch_to_scene2(self.video_path, self.is_arabic)
        else:
            # Show warning message for 3 seconds
            self.language_warning.setVisible(True)
            QTimer.singleShot(
                3000, lambda: self.language_warning.setVisible(False))
