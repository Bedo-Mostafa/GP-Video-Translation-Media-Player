import functools
import time
import threading
from datetime import datetime
import psutil
import asyncio


def performance_log(func):
    """
    Decorator to log performance metrics (execution time, CPU usage, RAM usage) for a function.
    Logs to 'performance_log.txt' in a thread-safe manner.
    """
    log_file = "performance_log.txt"
    log_lock = threading.Lock()

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent(interval=None)

        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = process.cpu_percent(interval=None)
            elapsed_time = end_time - start_time
            memory_used = end_memory - start_memory
            cpu_avg = (start_cpu + end_cpu) / 2

            log_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Function '{func.__name__}' completed in {elapsed_time:.2f}s | "
                f"CPU: {cpu_avg:.2f}% | RAM: {memory_used:.2f}MB\n"
            )
            with log_lock:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(log_message)

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent(interval=None)

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = process.cpu_percent(interval=None)
            elapsed_time = end_time - start_time
            memory_used = end_memory - start_memory
            cpu_avg = (start_cpu + end_cpu) / 2

            log_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Function '{func.__name__}' completed in {elapsed_time:.2f}s | "
                f"CPU: {cpu_avg:.2f}% | RAM: {memory_used:.2f}MB\n"
            )
            with log_lock:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(log_message)

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
