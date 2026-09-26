"""Design models: the sections an extra design document can contain (roadmap WP8).

Each :class:`Model` renders one section (heading + body) of one extra design document,
for example the dependency graph of ``technical_design``. Which models a document
contains is set per document with ``extra_designs.<document>.models`` in the config.

To add a model: write its render function, add a :class:`Model` to :data:`MODELS`, and add
its name to ``kingmadoc.config.DOCUMENT_MODELS`` (checked when this module is imported).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from kingmadoc.config import DOCUMENT_MODELS
from kingmadoc.diagrams.base import DiagramBackend
from kingmadoc.exceptions import GenerationError

if TYPE_CHECKING:
    from kingmadoc.plan.generator import PlanContext


@dataclass(frozen=True)
class Model:
    """One design model.

    Attributes:
        name: Value in ``extra_designs.<document>.models``.
        document: The extra design document it belongs to.
        title: Section heading.
        render: Returns the section body (Markdown, without the heading).
    """

    name: str
    document: str
    title: str
    render: Callable[[PlanContext, DiagramBackend], str]


MODELS: tuple[Model, ...] = ()


def render_model_sections(
    document: str, names: Sequence[str], context: PlanContext, backend: DiagramBackend
) -> list[str]:
    """Render the selected models of one document as Markdown sections.

    Args:
        document: Extra design name, e.g. ``"technical_design"``.
        names: Selected model names, in output order.
        context: The plan context.
        backend: Diagram backend for the configured ``diagram_format``.

    Returns:
        One ``## Title`` section per selected model.

    Raises:
        GenerationError: If a name is not a model of ``document``.
    """
    by_name = {m.name: m for m in MODELS if m.document == document}
    sections = []
    for name in names:
        model = by_name.get(name)
        if model is None:
            raise GenerationError(f"Unknown model {name!r} for {document}")
        sections.append(f"## {model.title}\n\n{model.render(context, backend).strip()}\n")
    return sections


def _check_models() -> None:
    """Fail at import time if :data:`MODELS` and ``config.DOCUMENT_MODELS`` disagree."""
    registered: dict[str, tuple[str, ...]] = {}
    for model in MODELS:
        registered[model.document] = (*registered.get(model.document, ()), model.name)
    configured = {document: names for document, names in DOCUMENT_MODELS.items() if names}
    if registered != configured:
        raise GenerationError(
            f"Design models {registered} do not match config.DOCUMENT_MODELS {configured}"
        )


_check_models()
