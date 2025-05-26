import psutil
import time
import statistics

SCRIPT_NAME = "main.py"
SAMPLE_INTERVAL = 1

def find_pid_by_script(script_name: str):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower() and script_name in ' '.join(proc.info['cmdline']):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def monitor_process(pid: int):
    proc = psutil.Process(pid)

    cpu_usages = []
    mem_usages = []

    print(f"Monitoring process {pid}...")

    try:
        while proc.is_running() and not proc.status() == psutil.STATUS_ZOMBIE:
            cpu = proc.cpu_percent(interval=SAMPLE_INTERVAL)
            mem = proc.memory_info().rss / 1024**2  # in MB

            cpu_usages.append(cpu)
            mem_usages.append(mem)

            print(f"CPU: {cpu:.2f}% | RAM: {mem:.2f} MB")
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        print("Process ended.")

    if cpu_usages and mem_usages:
        print("\n--- Final Stats ---")
        print(f"Avg CPU: {statistics.mean(cpu_usages):.2f}%")
        print(f"Max CPU: {max(cpu_usages):.2f}%")
        print(f"Avg RAM: {statistics.mean(mem_usages):.2f} MB")
        print(f"Max RAM: {max(mem_usages):.2f} MB")
    else:
        print("No data collected.")

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
