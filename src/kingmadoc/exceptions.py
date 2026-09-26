"""Custom exceptions raised by KingmaDoc."""


class KingmaDocError(Exception):
    """Base class for all KingmaDoc errors."""


class ConfigError(KingmaDocError):
    """Raised when `.featuredoc.yml` is missing, unreadable, or invalid."""


class AnalysisError(KingmaDocError):
    """Raised when the codebase cannot be analyzed."""


class GenerationError(KingmaDocError):
    """Raised when a document cannot be rendered or written."""
