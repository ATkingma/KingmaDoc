"""Diagram backends, selected by ``diagram_format`` in ``.featuredoc.yml``."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from kingmadoc.diagrams import d2, mermaid, plantuml
from kingmadoc.diagrams.base import DiagramBackend
from kingmadoc.exceptions import DiagramError

BACKENDS: Mapping[str, DiagramBackend] = MappingProxyType({
    "mermaid": mermaid,
    "plantuml": plantuml,
    "d2": d2,
})


def get_backend(diagram_format: str) -> DiagramBackend:
    """Return the backend module for ``diagram_format``.

    Args:
        diagram_format: ``mermaid``, ``plantuml`` or ``d2``.

    Returns:
        A module implementing :class:`~kingmadoc.diagrams.base.DiagramBackend`.

    Raises:
        DiagramError: If the format is unknown.
    """
    try:
        return BACKENDS[diagram_format]
    except KeyError:
        raise DiagramError(
            f"Unknown diagram_format {diagram_format!r}; supported: {', '.join(BACKENDS)}"
        ) from None
