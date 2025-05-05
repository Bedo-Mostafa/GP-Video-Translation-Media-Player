import threading
from datetime import datetime


class Logger:
    def __init__(self, log_file="log.txt"):
        self.log_file = log_file
        self.log_lock = threading.Lock()

    def log_step(self, step_name, elapsed_time, additional_info=None):
        """Log the time taken for a step to the log file in a thread-safe manner."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] Step '{step_name}' completed in {elapsed_time:.2f} seconds"
        if additional_info:
            log_message += f" | {additional_info}"
        log_message += "\n"
        with self.log_lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_message)
