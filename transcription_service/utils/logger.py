import threading
from datetime import datetime

class Logger:
    """Thread-safe logger for recording processing steps."""

    def __init__(self, log_file: str = "log.txt"):
        self.log_file = log_file
        self.log_lock = threading.Lock()

    def log_step(self, step_name: str, elapsed_time: float, additional_info: str = None):
        """Log the time taken for a step to the log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] Step '{step_name}' completed in {elapsed_time:.2f} seconds"
        if additional_info:
            log_message += f" | {additional_info}"
        log_message += "\n"
        with self.log_lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_message)