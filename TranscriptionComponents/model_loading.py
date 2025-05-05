import torch
from transformers import MarianMTModel, MarianTokenizer
from faster_whisper import WhisperModel
import os


def load_translation_model():
    """Load the MarianMT model and tokenizer from local directory."""
    model_path = os.path.join("models", "marianmt_en_ar")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"MarianMT model not found at {model_path}. Please download it first.")

    tokenizer = MarianTokenizer.from_pretrained(model_path)
    nmt_model = MarianMTModel.from_pretrained(model_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    nmt_model = nmt_model.to(device)
    return nmt_model, tokenizer


def load_whisper_model(model_name):
    """Load the Faster Whisper model from local directory."""
    if model_name in globals().get('model_cache', {}):
        return globals()['model_cache'][model_name]

    model_path = os.path.join("models", f"faster_whisper_{model_name}")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Faster Whisper model not found at {model_path}. Please download it first.")

    print(f"Loading Faster Whisper model '{model_name}' from {model_path}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = WhisperModel(model_path, device=device, compute_type="int8")
    if 'model_cache' not in globals():
        globals()['model_cache'] = {}
    globals()['model_cache'][model_name] = model
    return model
