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
