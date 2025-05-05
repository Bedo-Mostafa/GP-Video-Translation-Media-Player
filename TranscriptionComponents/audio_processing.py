import shutil
import subprocess
import numpy as np
import librosa
import webrtcvad
import noisereduce as nr
import soundfile as sf
import time


def get_video_duration(video_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())


def extract_audio_from_video(video_path, output_path, logger):
    print("Extracting audio from video...")
    start_time = time.time()
    extract_cmd = ["ffmpeg", "-y", "-i", video_path, "-vn",
                   "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path]
    try:
        result = subprocess.run(extract_cmd, check=True,
                                capture_output=True, text=True)
        elapsed_time = time.time() - start_time
        logger.log_step("Extract Audio from Video", elapsed_time,
                        f"Video: {video_path}, Output: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] FFmpeg failed: {e.stderr}")
        raise
    except FileNotFoundError:
        print(
            "[ERROR] FFmpeg not found. Please ensure FFmpeg is installed and added to your PATH.")
        raise


def get_speech_mask(audio, sr, logger, frame_duration_ms=30):
    start_time = time.time()
    vad = webrtcvad.Vad(3)
    frame_length = int(sr * frame_duration_ms / 1000)
    padded_audio = np.pad(
        audio, (0, frame_length - len(audio) % frame_length), mode='constant')
    frames = np.reshape(padded_audio, (-1, frame_length))
    speech_mask = np.zeros(len(audio), dtype=bool)
    for i, frame in enumerate(frames):
        byte_data = (frame * 32768).astype(np.int16).tobytes()
        is_speech = vad.is_speech(byte_data, sample_rate=sr)
        if is_speech:
            start = i * frame_length
            end = min((i + 1) * frame_length, len(audio))
            speech_mask[start:end] = True
    elapsed_time = time.time() - start_time
    logger.log_step("Get Speech Mask", elapsed_time,
                    f"Audio Length: {len(audio)} samples, Sample Rate: {sr} Hz")
    return speech_mask


def isolate_speech_focused(audio_path, output_speech_path, logger):
    start_time = time.time()
    try:
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        speech_mask = get_speech_mask(y, sr, logger)
        noise_profile = y[~speech_mask]
        if len(noise_profile) < 1:
            print(
                "[WARN] No noise profile could be generated, falling back to full audio")
            noise_profile = y
        reduced_audio = nr.reduce_noise(
            y=y, sr=sr, y_noise=noise_profile, stationary=False, prop_decrease=1.0, use_tqdm=True)
        sf.write(output_speech_path, reduced_audio, sr)
        print(f"[SUCCESS] Isolated speech saved to: {output_speech_path}")
        elapsed_time = time.time() - start_time
        logger.log_step("Isolate Speech Focused", elapsed_time,
                        f"Input: {audio_path}, Output: {output_speech_path}")
        return output_speech_path
    except Exception as e:
        print(f"[ERROR] Failed to isolate speech: {e}")
        elapsed_time = time.time() - start_time
        logger.log_step("Isolate Speech Focused (Failed)", elapsed_time,
                        f"Input: {audio_path}, Error: {str(e)}")
        return None


def prepare_audio(video_path, raw_audio_path, cleaned_audio_path, logger):
    start_time = time.time()
    extract_audio_from_video(video_path, raw_audio_path, logger)
    result = isolate_speech_focused(raw_audio_path, cleaned_audio_path, logger)
    if not result:
        print("[WARNING] Using original audio instead.")
        shutil.copy(raw_audio_path, cleaned_audio_path)
    elapsed_time = time.time() - start_time
    logger.log_step("Prepare Audio", elapsed_time,
                    f"Video: {video_path}, Raw: {raw_audio_path}, Cleaned: {cleaned_audio_path}")


def detect_silent_points(audio_path, logger, min_silence_duration=0.7, silence_threshold_db=-35):
    start_time = time.time()
    audio, sr = librosa.load(audio_path, sr=None)
    frame_length = 2048
    hop_length = 512
    rms = librosa.feature.rms(
        y=audio, frame_length=frame_length, hop_length=hop_length)[0]
    db = librosa.amplitude_to_db(rms, ref=np.max)
    silent_regions = []
    silent_start = None
    for i, value in enumerate(db):
        current_time = i * hop_length / sr
        if value < silence_threshold_db:
            if silent_start is None:
                silent_start = current_time
        else:
            if silent_start is not None:
                silent_duration = current_time - silent_start
                if silent_duration >= min_silence_duration:
                    midpoint = silent_start + silent_duration / 2
                    silent_regions.append(midpoint)
                silent_start = None
    elapsed_time = time.time() - start_time
    logger.log_step("Detect Silent Points", elapsed_time,
                    f"Audio: {audio_path}, Silent Regions Found: {len(silent_regions)}")
    return silent_regions


def segment_audio(audio_path, video_path, min_silence_duration, silence_threshold, logger):
    print("Detecting silent points for segmentation...")
    start_time = time.time()
    silent_points = detect_silent_points(
        audio_path, logger, min_silence_duration, silence_threshold)
    silent_points = sorted(set(round(p, 2) for p in silent_points))
    video_duration = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                    "default=noprint_wrappers=1:nokey=1", video_path], stdout=subprocess.PIPE, text=True, check=True)
    video_duration = float(video_duration.stdout.strip())
    if len(silent_points) < 3:
        print("Few silent points detected. Creating time-based segments...")
        segment_length = 30
        silent_points = [
            i * segment_length for i in range(1, int(video_duration / segment_length))]
    silent_points = [p for p in silent_points if p < video_duration - 1]
    elapsed_time = time.time() - start_time
    logger.log_step("Segment Audio", elapsed_time,
                    f"Audio: {audio_path}, Video: {video_path}, Segments: {len(silent_points)}")
    return silent_points


def create_segment_jobs(silent_points, video_duration, logger):
    start_time = time.time()
    points = [0.0] + silent_points + [video_duration]
    jobs = []
    for idx in range(len(points) - 1):
        start = points[idx]
        end = points[idx + 1]
        if start < end:
            jobs.append((start, end, idx))
    elapsed_time = time.time() - start_time
    logger.log_step("Create Segment Jobs", elapsed_time,
                    f"Total Jobs: {len(jobs)}, Video Duration: {video_duration:.2f}s")
    return jobs


def cut_audio_segment(input_audio, output_path, start_time, end_time, logger):
    start_time_segment = time.time()
    cmd = ["ffmpeg", "-y", "-ss",
           str(start_time), "-i", input_audio, "-loglevel", "error"]
    if end_time is not None:
        duration = float(end_time) - float(start_time)
        cmd.extend(["-t", str(duration)])
    cmd.append(output_path)
    subprocess.run(cmd, check=True, capture_output=True)
    elapsed_time = time.time() - start_time_segment
    logger.log_step("Cut Audio Segment", elapsed_time,
                    f"Input: {input_audio}, Output: {output_path}, Start: {start_time:.2f}s, End: {end_time if end_time is not None else 'N/A'}")
    return output_path
