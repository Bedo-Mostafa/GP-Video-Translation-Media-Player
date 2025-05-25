from typing import Dict  # Changed from List, Dict
from torch import no_grad

from services.utils.aspect import performance_log
from services.utils.logging_config import get_translation_logger  # Optional specific logger

logger = get_translation_logger()  # Using a specific logger if available


class Translator:
    def __init__(self):
        self.nmt_model = None
        self.tokenizer = None

    @performance_log
    def translate_segment(self, segment_data: Dict) -> Dict:
        """
        Translates the text within the provided segment dictionary.
        Expects segment_data: {"text": "...", "start": S, "end": E, "index": I}
        Returns the same dict with "text" translated.
        """
        original_text = segment_data.get("text", "")
        if not original_text:
            logger.warning(
                f"Segment {segment_data.get('index', 'N/A')} has no text to translate."
            )
            return segment_data  # Return original if no text

        try:
            inputs = self.tokenizer(
                original_text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,  # Ensure this is appropriate
            ).to(self.nmt_model.device)

            with no_grad():
                translated_ids = self.nmt_model.generate(
                    **inputs,
                    num_beams=1,  # Faster
                    max_length=512,  # Ensure this is appropriate
                    # early_stopping=True # Can enable
                )

            translated_text = self.tokenizer.decode(
                translated_ids[0], skip_special_tokens=True
            )

            # Create a new dictionary or update the existing one to ensure no side effects
            # and to maintain the structure.
            return {
                **segment_data,  # Copies all original fields like start, end, index
                "text": translated_text,
            }
        except Exception as e:
            logger.error(
                f"Translation error for segment {segment_data.get('index', 'N/A')}, text '{original_text[:50]}...': {e}",
                exc_info=True,
            )
            # Return original segment data with an error marker in text or a new field
            return {
                **segment_data,
                "text": f"[Translation Error] {original_text}",
            }
