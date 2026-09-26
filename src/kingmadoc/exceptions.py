"""Custom exceptions raised by KingmaDoc."""


class KingmaDocError(Exception):
    """Base class for all KingmaDoc errors."""


class ConfigError(KingmaDocError):
    """Raised when `.featuredoc.yml` is missing, unreadable, or invalid."""


class AnalysisError(KingmaDocError):
    """Raised when the codebase cannot be analyzed."""


class GenerationError(KingmaDocError):
    """Raised when a document cannot be rendered or written."""


class DiagramError(KingmaDocError):
    """Raised when diagram input is invalid (missing names, unknown relationship ends)."""


class VerificationError(KingmaDocError):
    """Raised when verify mode cannot run (e.g. the plan doc does not exist)."""


class AdrError(KingmaDocError):
    """Raised when an Architecture Decision Record cannot be created."""


class RenderError(KingmaDocError):
    """Raised when diagrams cannot be rendered to images (e.g. D2 missing or failing)."""


class ExplainError(KingmaDocError):
    """Raised when an explainer folder cannot be picked or created."""


class FactsError(KingmaDocError):
    """Raised when facts about the code cannot be collected (e.g. an unknown git base)."""
