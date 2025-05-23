from PySide6.QtWidgets import (
    QMainWindow,
    QGraphicsDropShadowEffect,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QSlider,
    QHBoxLayout,
    QSizePolicy,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsRectItem,
    QLabel,
    QProgressBar,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtCore import Qt, QTimer, QSizeF
from PySide6.QtGui import QFont, QBrush, QColor, QPainter


class VideoPlayerUI(QMainWindow):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.resize(800, 600)

        # Create central widget and layout
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Create a container widget for the graphics view
        video_container = QWidget()
        video_container.setObjectName("video_container")
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(0)

        # Create graphics view and scene for video and subtitles
        self.scene = QGraphicsScene()
        self.graphics_view = QGraphicsView(self.scene)
        self.graphics_view.setObjectName("video_widget")
        self.graphics_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setRenderHint(
            QPainter.SmoothPixmapTransform
        )  # Added for smoother video rendering
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        video_layout.addWidget(self.graphics_view)

        # Video item
        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)

        # Subtitle items (background and text)
        self.subtitle_background = QGraphicsRectItem()
        self.subtitle_background.setBrush(QBrush(QColor(0, 0, 0, 180)))  # Semi-transparent black
        self.subtitle_background.setPen(Qt.NoPen)
        self.scene.addItem(self.subtitle_background)

        self.subtitle_text = QGraphicsTextItem()
        self.subtitle_text.setFont(QFont("Arial", 16, QFont.Bold))
        self.subtitle_text.setDefaultTextColor(Qt.white)

        # Apply shadow effect to text
        shadow = QGraphicsDropShadowEffect()
        shadow.setOffset(2, 2)
        shadow.setBlurRadius(6)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.subtitle_text.setGraphicsEffect(shadow)

        # Center-justify the text within its box
        doc = self.subtitle_text.document()
        option = doc.defaultTextOption()
        option.setAlignment(Qt.AlignHCenter)
        doc.setDefaultTextOption(option)

        self.scene.addItem(self.subtitle_text)

        # Add buffering indicator
        self.buffering_indicator = QProgressBar()
        self.buffering_indicator.setObjectName("buffering_indicator")
        self.buffering_indicator.setRange(0, 0)  # Indeterminate mode
        self.buffering_indicator.setFixedHeight(3)
        self.buffering_indicator.setTextVisible(False)
        self.buffering_indicator.setVisible(False)  # Hidden by default
        video_layout.addWidget(self.buffering_indicator)

        layout.addWidget(video_container)

        # Media player setup
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_item)

        # Control bar
        control_bar = QWidget()
        control_bar.setObjectName("control_bar")
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(5, 5, 5, 5)
        control_layout.setSpacing(5)

        # Rewind button (⏪)
        self.rewind_button = QPushButton("⏪")
        self.rewind_button.setObjectName("rewind_button")
        self.rewind_button.setFixedSize(30, 30)
        control_layout.addWidget(self.rewind_button)

        # Play/Pause button
        self.play_button = QPushButton("⏯️")
        self.play_button.setObjectName("play_button")
        self.play_button.setFixedSize(30, 30)
        control_layout.addWidget(self.play_button)

        # Fast Forward button (⏩)
        self.forward_button = QPushButton("⏩")
        self.forward_button.setObjectName("forward_button")
        self.forward_button.setFixedSize(30, 30)
        control_layout.addWidget(self.forward_button)

        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setObjectName("progress_slider")
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.setValue(0)
        control_layout.addWidget(self.progress_slider)

        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("time_label")
        self.time_label.setFixedHeight(30)
        control_layout.addWidget(self.time_label)

        # Cancel button
        self.cancel_button = QPushButton("🏠")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setFixedSize(30, 30)
        control_layout.addWidget(self.cancel_button)

        # Volume button
        self.volume_button = QPushButton("🔊")
        self.volume_button.setObjectName("volume_button")
        self.volume_button.setFixedSize(30, 30)
        control_layout.addWidget(self.volume_button)

        # Volume slider (hidden by default)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setObjectName("volume_slider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setVisible(False)
        control_layout.addWidget(self.volume_slider)

        layout.addWidget(control_bar)

        # Initialize the scene size
        self.updateSceneRect()

        # Timer to handle video resize at startup
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.updateSceneRect)
        self.resize_timer.start(100)  # Adjust timing as needed

    def updateSceneRect(self):
        """Update the scene rectangle to match the view size"""
        view_size = self.graphics_view.size()
        # Make sure scene is at least as big as the view
        self.scene.setSceneRect(0, 0, view_size.width(), view_size.height())
        # Update video item size
        self.video_item.setSize(QSizeF(view_size.width(), view_size.height()))
        # Update subtitle positioning
        self.updateSubtitlePosition()

    def updateSubtitlePosition(self):
        """Update subtitle text position and background"""
        if not self.subtitle_text.toPlainText():
            # Hide background if no text
            self.subtitle_background.setVisible(False)
            return
        else:
            self.subtitle_background.setVisible(True)

        view_width = self.graphics_view.width()
        view_height = self.graphics_view.height()

        # Set text width for wrapping
        text_width = min(700, view_width - 40)  # Max width with margins
        self.subtitle_text.setTextWidth(text_width)

        # Ensure text alignment is centered
        doc = self.subtitle_text.document()
        option = doc.defaultTextOption()
        option.setAlignment(Qt.AlignHCenter)
        doc.setDefaultTextOption(option)

        # Get text rectangle after width is set
        text_rect = self.subtitle_text.boundingRect()

        # Center text horizontally, position near bottom
        text_x = (view_width - text_rect.width()) / 2
        text_y = view_height - text_rect.height() - 20  # More space from bottom

        # Set text position
        self.subtitle_text.setPos(text_x, text_y)

        # Set background position and size with padding
        padding = 10
        background_x = text_x - padding
        background_y = text_y - padding
        background_width = text_rect.width() + (padding * 2)
        background_height = text_rect.height() + (padding * 2)

        self.subtitle_background.setRect(
            background_x, background_y, background_width, background_height
        )

    def resizeEvent(self, event):
        """Handle widget resize events"""
        super().resizeEvent(event)
        self.updateSceneRect()
        # Ensure this triggers after the widget has fully resized
        QTimer.singleShot(50, self.updateSceneRect)

    def showEvent(self, event):
        """Handle widget show events"""
        super().showEvent(event)
        # Make sure video is properly sized when first shown
        QTimer.singleShot(100, self.updateSceneRect)

    def showBuffering(self, visible=True):
        """Show or hide the buffering indicator"""
        self.buffering_indicator.setVisible(visible)
