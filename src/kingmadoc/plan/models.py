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


STRIDE: tuple[tuple[str, str], ...] = (
    ("Spoofing", "Can someone pretend to be another user or system?"),
    ("Tampering", "Can data be changed in transit or at rest without anyone noticing?"),
    ("Repudiation", "Can someone deny an action because it is not logged?"),
    ("Information disclosure", "Can data reach someone who should not see it?"),
    ("Denial of service", "Can the feature be made slow or unavailable?"),
    ("Elevation of privilege", "Can someone do more than their role allows?"),
)


def _threat_model(context: PlanContext, backend: DiagramBackend) -> str:
    from kingmadoc.plan.generator import DATA_STORES, infer_containers  # avoid import cycle

    report = context.codebase_report
    containers = ", ".join(
        f"`{c['name']}`" for c in infer_containers(report, context.project_name)
    )
    stores = ", ".join(t for t in report.detected_stack if t in DATA_STORES) or "none detected"
    rows = "\n".join(
        f"| **{threat}** | {question} | _TODO_ | _TODO_ | open |" for threat, question in STRIDE
    )
    return f"""_(inferred)_ Elements to assess: the users of the feature; containers {containers};
data stores: {stores}; external systems: _TODO_.

Go through every threat for every element it applies to. Keep a row per threat that is
real, with its mitigation; write _not applicable_ (and why) for the others.

| Threat | Question | Applies to | Mitigation | Status |
|---|---|---|---|---|
{rows}"""


def _permissions(context: PlanContext, backend: DiagramBackend) -> str:
    return """One row per role, one column per action this feature adds or changes. Write
_allowed_, _denied_ or the condition (e.g. _own data only_).

| Role | _TODO: action 1_ | _TODO: action 2_ |
|---|---|---|
| Anonymous visitor | _TODO_ | _TODO_ |
| Signed-in user | _TODO_ | _TODO_ |
| Administrator | _TODO_ | _TODO_ |

- _TODO: where roles come from (and who can change them)._
- _TODO: what a denied request gets (hidden, disabled, error) and whether it is logged._"""


def _domain_model(context: PlanContext, backend: DiagramBackend) -> str:
    entity_a, entity_b = "Entity A (TODO)", "Entity B (TODO)"
    diagram = backend.render_class(
        "Domain model",
        [
            {"name": entity_a, "attributes": ["+id: str"]},
            {"name": entity_b, "attributes": ["+id: str", "+entity_a_id: str"]},
        ],
        [(entity_b, entity_a, "association", "belongs to")],
    )
    return f"""The concepts this feature works with: entities, value objects and aggregates, with
their relationships. _TODO: replace the example entities._

{diagram}

- _TODO: rules that must always hold for these objects (invariants)._"""


def _event_storming(context: PlanContext, backend: DiagramBackend) -> str:
    return """What happens in the domain, in time order. In a workshop these are sticky notes:
domain events orange, commands blue, actors yellow, policies purple.

| # | Domain event (past tense) | Command (what caused it) | Actor | Policy (when …, then …) |
|---|---|---|---|---|
| 1 | _TODO: e.g. "Password reset requested"_ | _TODO_ | _TODO_ | _TODO_ |
| 2 | _TODO_ | _TODO_ | _TODO_ | _TODO_ |
| 3 | _TODO_ | _TODO_ | _TODO_ | _TODO_ |"""


MODELS: tuple[Model, ...] = (
    Model("domain_model", "domain_design", "Domain model", _domain_model),
    Model("event_storming", "domain_design", "Event storming", _event_storming),
    Model("threat_model", "security_design", "Threat model (STRIDE)", _threat_model),
    Model("permissions", "security_design", "Permissions: who may do what", _permissions),
)


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
