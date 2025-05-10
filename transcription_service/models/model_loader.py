import os

import torch
from faster_whisper import WhisperModel
from transformers import MarianMTModel, MarianTokenizer


def load_translation_model():
    """Load the MarianMT model and tokenizer from local directory."""
    model_path = os.path.join("models", "marianmt_en_ar_distilled")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"MarianMT model not found at {model_path}. Please download it first."
        )
    tokenizer = MarianTokenizer.from_pretrained(model_path)
    nmt_model = MarianMTModel.from_pretrained(model_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    nmt_model = nmt_model.to(device)
    return nmt_model, tokenizer


def load_whisper_model(model_name: str) -> WhisperModel:
    """Load the Faster Whisper model from local directory."""
    model_path = os.path.join("models", f"faster_whisper_{model_name}")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Faster Whisper model not found at {model_path}. Please download it first."
        )
    print(f"Loading Faster Whisper model '{model_name}' from {model_path}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return WhisperModel(
        model_path, device=device, compute_type="int8", cpu_threads=2, num_workers=5
    )
