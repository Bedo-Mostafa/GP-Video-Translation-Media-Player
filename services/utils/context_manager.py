from services.config.context import ProcessingContext


class ContextManager:
    """Manages the global ProcessingContext."""

    _context: ProcessingContext = None

    @classmethod
    def set_context(cls, context: ProcessingContext) -> None:
        """Sets the global ProcessingContext."""
        cls._context = context

    @classmethod
    def get_context(cls) -> ProcessingContext:
        """Returns the global ProcessingContext."""
        return cls._context

    @classmethod
    def get_transcript_file(cls, is_lock=False, lang=None) -> str:
        """Returns the path to the transcript file for the specified language."""
        context = cls.get_context()
        if lang is None:
            lang = context.tgt_lang
        return context.get_srt_file(lang, is_lock)
