from services.utils.context_manager import ContextManager


def get_transcript_file(is_lock=False):
    context = ContextManager.get_context()
    return context.get_srt_file(context.tgt_lang, is_lock)


# Configuration settings for the video player application
DEFAULT_SERVER_PORT = 8000
API_BASE_URL = "http://localhost:{port}"
UPLOAD_TIMEOUT = 600  # seconds
CANCEL_TIMEOUT = 5  # seconds
SERVER_HEALTH_CHECK_TIMEOUT = 2  # seconds
SERVER_START_MAX_ATTEMPTS = 30
BUFFERING_CHECK_INTERVAL = 100  # ms
SUBTITLE_UPDATE_INTERVAL = 10
