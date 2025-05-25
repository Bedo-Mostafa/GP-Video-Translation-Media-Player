import functools
import time
import threading
from datetime import datetime
import psutil
import os
from asyncio import create_task, sleep, iscoroutinefunction


class PerformanceMetrics:
    """Class to store and manage performance metrics."""
    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.end_memory = None
        self.start_cpu = psutil.Process().cpu_percent(interval=None)
        self.end_cpu = None
        self.peak_memory = self.start_memory
        self.cpu_samples = [self.start_cpu]
        self.thread_count = threading.active_count()
        self.function_args = None
        self.function_kwargs = None
        self.exception = None

    def update_metrics(self):
        """Update metrics during execution."""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)
        self.cpu_samples.append(psutil.Process().cpu_percent(interval=None))

    def finalize(self):
        """Finalize metrics after execution."""
        self.end_time = time.time()
        self.end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.end_cpu = psutil.Process().cpu_percent(interval=None)
        self.cpu_samples.append(self.end_cpu)

    def format_mini_metrics(self, func_name: str) -> str:
        """Format a mini version of the metrics for quick insights."""
        execution_time = self.end_time - self.start_time
        memory_change = self.end_memory - self.start_memory
        cpu_peak = max(self.cpu_samples)
        
        # Format the timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Create a compact one-line summary
        status = "❌" if self.exception else "✓"
        return (
            f"[{timestamp}] {status} {func_name:<30} "
            f"⏱️ {execution_time:>6.2f}s | "
            f"📊 CPU: {cpu_peak:>5.1f}% | "
            f"💾 RAM: {memory_change:>+6.1f}MB"
        )

    def format_metrics(self, func_name: str, module_name: str) -> str:
        """Format metrics into a human-readable string."""
        execution_time = self.end_time - self.start_time
        memory_change = self.end_memory - self.start_memory
        cpu_avg = sum(self.cpu_samples) / len(self.cpu_samples)
        cpu_peak = max(self.cpu_samples)

        # Format the timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a formatted string with clear sections
        output = [
            f"\n{'='*80}",
            f"Performance Log Entry - {timestamp}",
            f"{'='*80}",
            f"\nFunction Details:",
            f"  Name: {func_name}",
            f"  Module: {module_name}",
            f"  Thread Count: {self.thread_count}",
            f"\nExecution Time:",
            f"  Total: {execution_time:.2f} seconds",
            f"\nMemory Usage:",
            f"  Start: {self.start_memory:.1f} MB",
            f"  End: {self.end_memory:.1f} MB",
            f"  Peak: {self.peak_memory:.1f} MB",
            f"  Change: {memory_change:+.1f} MB",
            f"\nCPU Usage:",
            f"  Start: {self.start_cpu:.1f}%",
            f"  End: {self.end_cpu:.1f}%",
            f"  Average: {cpu_avg:.1f}%",
            f"  Peak: {cpu_peak:.1f}%"
        ]

        # Add arguments if they exist
        if self.function_args or self.function_kwargs:
            output.extend([
                f"\nArguments:",
                f"  Args: {self.function_args}",
                f"  Kwargs: {self.function_kwargs}"
            ])

        # Add exception if it occurred
        if self.exception:
            output.extend([
                f"\nException:",
                f"  {str(self.exception)}"
            ])

        output.append(f"\n{'-'*80}\n")
        return "\n".join(output)


def performance_log(func):
    """
    Enhanced decorator to log detailed performance metrics for a function.
    Logs to both a detailed text file and a mini-summary file.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    detailed_log = os.path.join(log_dir, "performance_log.txt")
    mini_log = os.path.join(log_dir, "performance_mini.txt")
    log_lock = threading.Lock()

    # Clear log files on startup
    with log_lock:
        try:
            open(detailed_log, 'w').close()
            open(mini_log, 'w').close()
        except Exception as e:
            print(f"Error clearing log files: {e}")

    def write_logs(metrics: PerformanceMetrics):
        """Write metrics to both log files in a thread-safe manner."""
        with log_lock:
            try:
                # Write detailed log
                with open(detailed_log, "a", encoding="utf-8") as f:
                    f.write(metrics.format_metrics(func.__name__, func.__module__))
                
                # Write mini log
                with open(mini_log, "a", encoding="utf-8") as f:
                    f.write(metrics.format_mini_metrics(func.__name__) + "\n")
            except Exception as e:
                print(f"Error writing performance logs: {e}")

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        metrics = PerformanceMetrics()
        metrics.function_args = args
        metrics.function_kwargs = kwargs

        try:
            # Start periodic metric updates
            update_timer = create_task(periodic_update(metrics))
            result = await func(*args, **kwargs)
            update_timer.cancel()
            return result
        except Exception as e:
            metrics.exception = e
            raise
        finally:
            metrics.finalize()
            write_logs(metrics)

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        metrics = PerformanceMetrics()
        metrics.function_args = args
        metrics.function_kwargs = kwargs

        try:
            # Start periodic metric updates in a separate thread
            update_thread = threading.Thread(
                target=periodic_update_sync,
                args=(metrics,),
                daemon=True
            )
            update_thread.start()
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            metrics.exception = e
            raise
        finally:
            metrics.finalize()
            write_logs(metrics)

    async def periodic_update(metrics: PerformanceMetrics):
        """Periodically update metrics during async execution."""
        while True:
            metrics.update_metrics()
            await sleep(0.1)

    def periodic_update_sync(metrics: PerformanceMetrics):
        """Periodically update metrics during sync execution."""
        while True:
            metrics.update_metrics()
            time.sleep(0.1)

    return async_wrapper if iscoroutinefunction(func) else sync_wrapper
