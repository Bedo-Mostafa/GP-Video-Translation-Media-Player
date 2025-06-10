from filelock import FileLock, Timeout
from PySide6.QtMultimedia import QMediaPlayer
from services.utils.context_manager import ContextManager
from utils.config import SUBTITLE_UPDATE_INTERVAL
from utils.logging_config import setup_logging
from os import path
from re import match, search
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGraphicsTextItem


class SubtitleManager:
    """Manages subtitle parsing and display."""

    def __init__(
        self,
        media_player: QMediaPlayer,
        subtitle_text: QGraphicsTextItem,
        update_subtitle_position,
        timer: QTimer,
    ):
        self.logger = setup_logging()
        self.media_player = media_player
        self.subtitle_text = subtitle_text
        self.update_subtitle_position = update_subtitle_position
        self.timer = timer
        self.transcript_segments = []
        self.waiting_for_subtitle = True
        self.is_transcription_complete = False
        self.update_counter = 0
        self.update_interval = SUBTITLE_UPDATE_INTERVAL

        self.timer.timeout.connect(self.check_subtitle)

    def load_initial_transcription(self):
        """Load initial transcription from file."""

        transcript_file = ContextManager.get_transcript_file()
        try:
            if path.exists(transcript_file):
                with open(transcript_file, "r", encoding="utf-8") as f:
                    self.parse_srt_transcription(f.read())
                self.logger.info(
                    "Loaded initial SRT transcription from %s", transcript_file
                )
        except Exception as e:
            self.logger.error("Error reading initial transcription: %s", str(e))

    def parse_srt_transcription(self, transcription):
        """Parse SRT transcription text into segments."""
        new_segments = []
        subtitle_blocks = transcription.strip().split("\n\n")
        for block in subtitle_blocks:
            if not block.strip():
                continue
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue
            try:
                _ = int(lines[0])
                time_line = lines[1]
                time_match = match(
                    r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                    time_line,
                )
                if not time_match:
                    self.logger.error(f"Invalid time format in line: {time_line}")
                    continue
                start_time = self._srt_time_to_seconds(time_match.group(1))
                end_time = self._srt_time_to_seconds(time_match.group(2))
                text = "\n".join(lines[2:])
                new_segments.append(
                    {"start": start_time, "end": end_time, "text": text.strip()}
                )
            except ValueError as e:
                self.logger.error(
                    f"Error parsing SRT block: {block[:50]}... - {str(e)}"
                )
                continue
        if new_segments:
            self.transcript_segments = new_segments
            self.logger.debug(f"Refreshed with {len(new_segments)} SRT segments")

    def _srt_time_to_seconds(self, srt_time):
        """Convert SRT time format (HH:MM:SS,mmm) to seconds."""
        time_part, ms_part = srt_time.split(",")
        hours, minutes, seconds = map(int, time_part.split(":"))
        milliseconds = int(ms_part)
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

    def parse_transcription(self, transcription):
        """Parse transcription text into segments (legacy method)."""
        if "-->" in transcription and search(r"\d{2}:\d{2}:\d{2},\d{3}", transcription):
            self.parse_srt_transcription(transcription)
        else:
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
                        self.logger.error(f"Error parsing transcription line: %s", line)
                        continue
            if new_segments:
                self.transcript_segments = new_segments

    def set_transcription_complete(self):
        """Mark transcription as complete."""
        self.is_transcription_complete = True
        self.logger.info("Transcription marked as complete")
        self.check_subtitle()

    def check_subtitle(self):
        """Update subtitle display and manage playback."""
        current_time = self.media_player.position() / 1000.0
        current_text = ""
        found_subtitle = False

        for segment in self.transcript_segments:
            if segment["start"] <= current_time <= segment["end"]:
                current_text = segment["text"]
                found_subtitle = True
                break

        if found_subtitle:
            if self.subtitle_text.toPlainText() != current_text:
                self.subtitle_text.setPlainText(current_text)
                self.update_subtitle_position()
        else:
            if self.subtitle_text.toPlainText() != "":
                self.subtitle_text.setPlainText("")
                self.update_subtitle_position()

        current_playback_state = self.media_player.playbackState()

        # Handle playback based on subtitle availability and transcription status
        if not self.is_transcription_complete and not found_subtitle:
            # No subtitle for current time and transcription is ongoing
            if self.transcript_segments:
                # Check if we're past the last known segment
                last_segment_end = self.transcript_segments[-1]["end"]
                if (
                    current_time >= last_segment_end
                    and current_playback_state == QMediaPlayer.PlayingState
                ):
                    self.media_player.pause()
                    self.waiting_for_subtitle = True
                    self.logger.info(
                        f"Paused at {current_time:.2f}s: No subtitle available, past last segment ({last_segment_end:.2f}s)."
                    )
            elif (
                current_time > 0.2
                and current_playback_state == QMediaPlayer.PlayingState
            ):
                # No segments at all, and we're past initial startup
                self.media_player.pause()
                self.waiting_for_subtitle = True
                self.logger.info(
                    "Paused: No subtitle segments available and transcription ongoing."
                )
        elif self.waiting_for_subtitle and (
            found_subtitle or self.is_transcription_complete
        ):
            # Resume playback if we were waiting and now have subtitles or transcription is complete
            self.waiting_for_subtitle = False
            if current_playback_state != QMediaPlayer.PlayingState:
                self.media_player.play()
                self.logger.info(
                    "Resumed playback: %s",
                    "Subtitle found" if found_subtitle else "Transcription complete",
                )

        self.update_counter += 1
        if self.update_counter >= self.update_interval:
            self.update_counter = 0
            self.refresh_transcription()

    def refresh_transcription(self):
        """Refresh transcription from file."""
        transcript_file = ContextManager.get_transcript_file()
        transcript_lock_file = ContextManager.get_transcript_file(is_lock=True)
        try:
            if not path.exists(transcript_file):
                return
            lock = FileLock(transcript_lock_file, timeout=0.5)
            with lock:
                with open(transcript_file, "r", encoding="utf-8") as f:
                    self.parse_srt_transcription(f.read())
        except Timeout:
            self.logger.warning(
                "Transcription file locked during refresh, will retry later."
            )
            return
        except Exception as e:
            self.logger.error(f"Error refreshing transcription: %s", str(e))
