# GP-Video-Translation-Media-Player

**GP-Video-Translation-Media-Player** is a powerful desktop application designed for seamless video viewing with real-time transcription and translation capabilities. This tool allows users to watch videos in one language while simultaneously reading subtitles in another, making content more accessible and understandable across linguistic barriers.

## Features

*   **Real-time Transcription:** Utilizes advanced speech-to-text models (e.g., Faster Whisper) to generate accurate transcriptions of video audio.
*   **Instant Translation:** Leverages neural machine translation models (e.g., MarianMT) to translate transcribed text into a wide array of target languages.
*   **Integrated Media Player:** Provides a user-friendly interface for video playback with synchronized display of original and translated subtitles.
*   **Customizable Models:** Supports configuration for different transcription and translation models to suit various performance and accuracy needs.
*   **Efficient Processing:** Employs a producer-consumer pipeline architecture for smooth, real-time performance, minimizing lag and resource overload.
*   **Cross-Platform (Potential):** Built with Python and Qt (PySide6), aiming for broad compatibility (though current focus might be on a specific OS, the underlying tech supports cross-platform).

## Core Technologies

*   **Python:** Main programming language.
*   **PySide6 (Qt for Python):** For the graphical user interface.
*   **Faster Whisper:** For high-performance speech-to-text transcription.
*   **MarianMT:** For efficient neural machine translation.
*   **FFmpeg:** For video and audio processing (implicitly used by libraries or directly for audio extraction).
*   **NumPy:** For numerical operations, especially in audio processing.

## Project Structure Overview

### Install Dependencies
   *   Python 3.8+ (Recommended: 3.10 or 3.11 for best compatibility with all dependencies)
   *   `pip` (Python package installer)
   *   Git (for cloning the repository)
   *   **FFmpeg:** This project relies on FFmpeg for audio and video processing. You'll need to install it and add it to your system's PATH.
       *   **Windows:**
           1.  Download the latest FFmpeg static build from the official [FFmpeg website](https://ffmpeg.org/download.html) (e.g., from the gyan.dev builds or BtbN builds linked there).
           2.  Extract the downloaded archive (e.g., to `C:\ffmpeg`).
           3.  Add the `bin` directory (e.g., `C:\ffmpeg\bin`) to your system's PATH environment variable. You can do this by:
               *   Searching for "environment variables" in the Windows search bar.
               *   Clicking on "Edit the system environment variables."
               *   In the System Properties window, click the "Environment Variables..." button.
               *   Under "System variables," find and select the `Path` variable, then click "Edit...".
               *   Click "New" and add the path to your FFmpeg `bin` directory.
               *   Click OK on all open windows to save the changes.
               *   You may need to restart your terminal or computer for the changes to take effect.
       *   **macOS (using Homebrew):**
           ```bash
           brew install ffmpeg
           ```
       *   **Linux (using apt, for Debian/Ubuntu-based systems):**
           ```bash
           sudo apt update
           sudo apt install ffmpeg
           ```
   *   **For GPU Acceleration (Recommended for significantly faster performance):**
   *   An NVIDIA GPU with an appropriate CUDA Toolkit installed. You can find the toolkit on the [NVIDIA Developer website](https://developer.nvidia.com/cuda-downloads).
   *   Ensure your NVIDIA drivers are up to date.
   
   ### Installation
   
   1.  **Ensure FFmpeg is installed and in PATH** (see Prerequisites above).
   
   2.  **Clone the repository:**
       ```bash
       git clone https://github.com/your-username/GP-Video-Translation-Media-Player.git
       cd GP-Video-Translation-Media-Player
       ```
   
   3.  **Create a virtual environment (recommended):**
       ```bash
       python -m venv venv
       # On Windows
       .\venv\Scripts\activate
       # On macOS/Linux
       source venv/bin/activate
       ```
   
   4.  **Install PyTorch with CUDA (if applicable):**
       If you have an NVIDIA GPU and have installed the CUDA Toolkit, run the `install_CUDA.py` script located in the project root. This script will attempt to detect your CUDA version and install the appropriate PyTorch build for GPU acceleration.
       ```bash
       python install_CUDA.py
       ```
       If you do not have an NVIDIA GPU, or if the script cannot detect a compatible CUDA version, it will guide you towards or install a CPU-only version of PyTorch. You can also skip this step if you intend to install PyTorch manually or rely on the `requirements.txt` for a CPU version.
   
   5.  **Install other dependencies:**
       After setting up PyTorch (if applicable via the script), install all other project dependencies:
       ```bash
       pip install -r requirements.txt
       ```
       *Note: If PyTorch was installed by `install_CUDA.py`, `pip` will recognize it and not attempt to reinstall a different version unless specified in `requirements.txt` with a conflicting version or build.*