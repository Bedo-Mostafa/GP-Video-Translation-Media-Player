from faster_whisper import WhisperModel


def transcribe_segment(model: WhisperModel, audio_file: str, start_time: float, end_time: float) -> list:
    """Transcribe an audio segment using Faster Whisper."""
    try:
        segments, _ = model.transcribe(audio_file, language="en", beam_size=5)
        adjusted_segments = []
        for segment in segments:
            segment_start = max(segment.start + start_time, start_time)
            segment_end = min(segment.end + start_time, end_time)
            if segment_start < segment_end:
                adjusted_segments.append({
                    "start": segment_start,
                    "end": segment_end,
                    "text": segment.text.strip()
                })
        return adjusted_segments
    except Exception as e:
        print(f"Error transcribing segment: {e}")
        return []


def write_srt_segment(segment, srt_path, index):
    with open(srt_path, "a", encoding="utf-8") as f:
        start = format_timestamp(segment['start'])
        end = format_timestamp(segment['end'])
        f.write(f"{index}\n")
        f.write(f"{start} --> {end}\n")
        f.write(f"{segment['text'].strip()}\n\n")


def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
