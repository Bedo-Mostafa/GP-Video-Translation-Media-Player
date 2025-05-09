import subprocess
import sys
import platform
import re
import shutil


def get_installed_cuda_version():
    """Extracts the CUDA version from nvidia-smi if available."""
    if not shutil.which("nvidia-smi"):
        print("❌ 'nvidia-smi' not found. No NVIDIA GPU detected.")
        return None

    try:
        output = subprocess.check_output(["nvidia-smi"], encoding="utf-8")
        match = re.search(r"CUDA Version:\s+(\d+\.\d+)", output)
        if match:
            cuda_version = match.group(1)
            print(f"✅ Detected CUDA version: {cuda_version}")
            return cuda_version
    except Exception as e:
        print("⚠️ Error running nvidia-smi:", e)

    return None


def install_pytorch(cuda_version=None):
    # Map closest CUDA versions to PyTorch URLs
    torch_versions = {
        "12.1": "https://download.pytorch.org/whl/cu121",
        "11.8": "https://download.pytorch.org/whl/cu118",
        "11.7": "https://download.pytorch.org/whl/cu117",
        "11.6": "https://download.pytorch.org/whl/cu116",
        "cpu":   "https://download.pytorch.org/whl/cpu"
    }

    # Pick matching or closest lower version
    selected_version = "cpu"
    if cuda_version:
        for ver in sorted(torch_versions.keys(), reverse=True):
            if ver != "cpu" and cuda_version.startswith(ver):
                selected_version = ver
                break

    torch_url = torch_versions[selected_version]
    print(f"📦 Installing PyTorch with compute support: {selected_version}")

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "torch", "torchvision", "torchaudio",
            "--index-url", torch_url
        ])
        print("✅ PyTorch installed successfully.")
    except subprocess.CalledProcessError as e:
        print("❌ PyTorch installation failed:", e)


if __name__ == "__main__":
    print("🔍 Platform:", platform.system(), platform.machine())
    cuda_ver = get_installed_cuda_version()
    install_pytorch(cuda_ver)
    print("💡 Done. Run `import torch; print(torch.cuda.is_available())` to test.")
