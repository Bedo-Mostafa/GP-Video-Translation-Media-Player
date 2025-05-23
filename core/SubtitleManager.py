from filelock import FileLock, Timeout
from PySide6.QtMultimedia import QMediaPlayer
from utils.config import (
    TRANSCRIPT_FILE,
    TRANSCRIPT_LOCK_FILE,
    SUBTITLE_UPDATE_INTERVAL,
)
from utils.logging_config import setup_logging
import os
import re


class SubtitleManager:
    """Manages subtitle parsing and display."""

    def __init__(self, media_player, subtitle_text, update_subtitle_position, timer):
        self.logger = setup_logging()
        self.media_player = media_player
        self.subtitle_text = subtitle_text
        self.update_subtitle_position = update_subtitle_position
        self.timer = timer
        self.transcript_segments = []
        self.waiting_for_subtitle = False
        self.update_counter = 0
        self.update_interval = SUBTITLE_UPDATE_INTERVAL
        self.timer.timeout.connect(self.check_subtitle)

    def load_initial_transcription(self):
        """Load initial transcription from file."""
        try:
            if os.path.exists(TRANSCRIPT_FILE):
                with open(TRANSCRIPT_FILE, "r", encoding="utf-8") as f:
                    self.parse_srt_transcription(f.read())
                self.logger.info(
                    "Loaded initial SRT transcription from %s", TRANSCRIPT_FILE
                )
        except Exception as e:
            self.logger.error("Error reading initial transcription: %s", str(e))

    def parse_srt_transcription(self, transcription):
        """Parse SRT transcription text into segments."""
        new_segments = []

        # Split by double newlines to get individual subtitle blocks
        subtitle_blocks = transcription.strip().split("\n\n")

        for block in subtitle_blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue

            try:
                # First line should be the sequence number
                sequence_num = int(lines[0])

                # Second line should be the time range
                time_line = lines[1]
                time_match = re.match(
                    r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                    time_line,
                )

                if not time_match:
                    self.logger.error(f"Invalid time format in line: {time_line}")
                    continue

                start_time = self._srt_time_to_seconds(time_match.group(1))
                end_time = self._srt_time_to_seconds(time_match.group(2))

                # Remaining lines are the text content
                text = "\n".join(lines[2:])

                new_segments.append(
                    {"start": start_time, "end": end_time, "text": text.strip()}
                )

            except (ValueError, IndexError) as e:
                self.logger.error(
                    f"Error parsing SRT block: {block[:50]}... - {str(e)}"
                )
                continue

        if new_segments:
            self.transcript_segments = new_segments
            self.logger.info(f"Parsed {len(new_segments)} SRT segments")

    def _srt_time_to_seconds(self, srt_time):
        """Convert SRT time format (HH:MM:SS,mmm) to seconds."""
        time_part, ms_part = srt_time.split(",")
        hours, minutes, seconds = map(int, time_part.split(":"))
        milliseconds = int(ms_part)
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

    def parse_transcription(self, transcription):
        """Parse transcription text into segments (legacy method for backwards compatibility)."""
        # Check if it's SRT format or old format
        if "-->" in transcription and re.search(
            r"\d{2}:\d{2}:\d{2},\d{3}", transcription
        ):
            self.parse_srt_transcription(transcription)
        else:
            # Handle old format for backwards compatibility
            new_segments = []
            for line in transcription.strip().split("\n"):
                if line:
                    try:
                        time_str, text = line.split("]", 1)
                        time_str = time_str[1:]
                        start_str, end_str = time_str.split("-")
                        start = float(start_str.strip())
                        end = float(end_str.strip())
                        new_segments.append(
                            {"start": start, "end": end, "text": text.strip()}
                        )
                    except Exception as e:
                        self.logger.error("Error parsing transcription line: %s", line)
                        continue
            if new_segments:
                self.transcript_segments = new_segments

    def check_subtitle(self):
        """Update subtitle display based on current video position."""
        current_time = self.media_player.position() / 1000.0
        current_text = ""
        found_subtitle = False
        has_future_subtitles = False

        for segment in self.transcript_segments:
            if segment["start"] <= current_time <= segment["end"]:
                current_text = segment["text"]
                found_subtitle = True
                break
            elif segment["start"] > current_time:
                has_future_subtitles = True

        if found_subtitle:
            if self.subtitle_text.toPlainText() != current_text:
                self.subtitle_text.setPlainText(current_text)
                self.update_subtitle_position()
            if self.waiting_for_subtitle:
                self.media_player.play()
                self.waiting_for_subtitle = False
        else:
            if (
                self.media_player.playbackState() == QMediaPlayer.PlayingState
                and not self.waiting_for_subtitle
                and not has_future_subtitles
            ):
                self.media_player.pause()
                self.waiting_for_subtitle = True
            elif has_future_subtitles and self.waiting_for_subtitle:
                self.logger.info("Future subtitles found. Resuming playback")
                self.media_player.play()
                self.waiting_for_subtitle = False

        self.update_counter += 1
        if self.update_counter >= self.update_interval:
            self.update_counter = 0
            self.refresh_transcription()

    def refresh_transcription(self):
        """Refresh transcription from file."""
        try:
            if not os.path.exists(TRANSCRIPT_FILE):
                return
            current_position = self.media_player.position()
            try:
                lock = FileLock(TRANSCRIPT_LOCK_FILE, timeout=0.5)
                with lock:
                    with open(TRANSCRIPT_FILE, "r", encoding="utf-8") as f:
                        self.parse_srt_transcription(f.read())
            except Timeout:
                self.logger.warning("Transcription file locked, will retry later")
                return
            if self.media_player.position() != current_position:
                self.media_player.setPosition(current_position)
                self.logger.debug("Restored video position after transcription refresh")
        except Exception as e:
            self.logger.error("Error refreshing transcription: %s", str(e))
