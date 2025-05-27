from services.api.routes import get_context
import os

# Configuration settings for the video player application
TRANSCRIPT_DIR = "transcriptions/"

def get_transcript_file():
    context = get_context()
    if context is None:
        return os.path.join(TRANSCRIPT_DIR, "transcription.srt")
    video_hash = context.get_video_hash()
    return os.path.join(TRANSCRIPT_DIR, f"{video_hash}.srt")

def get_transcript_lock_file():
    context = get_context()
    if context is None:
        return os.path.join(TRANSCRIPT_DIR, "transcription.srt.lock")
    video_hash = context.get_video_hash()
    return os.path.join(TRANSCRIPT_DIR, f"{video_hash}.srt.lock")

DEFAULT_SERVER_PORT = 8000
API_BASE_URL = "http://localhost:{port}"
UPLOAD_TIMEOUT = 600  # seconds
CANCEL_TIMEOUT = 5  # seconds
SERVER_HEALTH_CHECK_TIMEOUT = 2  # seconds
SERVER_START_MAX_ATTEMPTS = 30
BUFFERING_CHECK_INTERVAL = 100  # ms
SUBTITLE_UPDATE_INTERVAL = 10
