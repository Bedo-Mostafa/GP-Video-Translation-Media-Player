import psutil
import time
import statistics
import subprocess
import shutil

SCRIPT_NAME = "main.py"
SAMPLE_INTERVAL = 1


def find_pid_by_script(script_name: str):
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "python" in proc.info["name"].lower() and script_name in " ".join(
                proc.info["cmdline"]
            ):
                return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def get_nvidia_gpu_usage():
    try:
        result = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
            ],
            encoding="utf-8",
        ).strip()
        usage, mem = map(int, result.split(","))
        return usage, mem
    except Exception:
        return None, None


def get_gpu_usage():
    if shutil.which("nvidia-smi"):
        return get_nvidia_gpu_usage()
    else:
        return None, None


def monitor_process(pid: int):
    proc = psutil.Process(pid)

    cpu_usages = []
    mem_usages = []

    gpu_usages = []
    gpu_mem_usages = []

    print(f"Monitoring process {pid}...")

    try:
        while proc.is_running() and not proc.status() == psutil.STATUS_ZOMBIE:
            cpu = proc.cpu_percent(interval=SAMPLE_INTERVAL)
            mem = proc.memory_info().rss / 1024**2  # in MB

            gpu_util, gpu_mem = get_gpu_usage()

            cpu_usages.append(cpu)
            mem_usages.append(mem)

            if gpu_util is not None and gpu_mem is not None:
                gpu_usages.append(gpu_util)
                gpu_mem_usages.append(gpu_mem)
                print(
                    f"CPU: {cpu:.2f}% | RAM: {mem:.2f} MB | GPU: {gpu_util}% | GPU RAM: {gpu_mem} MB"
                )
            else:
                print(f"CPU: {cpu:.2f}% | RAM: {mem:.2f} MB")

    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        print("Process ended.")

    print("\n--- Final Stats ---")

    if cpu_usages:
        print(f"Avg CPU: {statistics.mean(cpu_usages):.2f}%")
        print(f"Max CPU: {max(cpu_usages):.2f}%")

    if mem_usages:
        print(f"Avg RAM: {statistics.mean(mem_usages):.2f} MB")
        print(f"Max RAM: {max(mem_usages):.2f} MB")

    if gpu_usages:
        print(f"Avg GPU Util: {statistics.mean(gpu_usages):.2f}%")
        print(f"Max GPU Util: {max(gpu_usages):.2f}%")

    if gpu_mem_usages:
        print(f"Avg GPU RAM: {statistics.mean(gpu_mem_usages):.2f} MB")
        print(f"Max GPU RAM: {max(gpu_mem_usages):.2f} MB")


def main():
    print("Waiting for process to start...")

    pid = None
    while pid is None:
        pid = find_pid_by_script(SCRIPT_NAME)
        if pid is None:
            time.sleep(1)

    monitor_process(pid)


if __name__ == "__main__":
    main()
