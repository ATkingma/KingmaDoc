"""Design models: the sections an extra design document can contain (roadmap WP8).

Each :class:`Model` renders one section (heading + body) of one extra design document,
for example the dependency graph of ``technical_design``. Which models a document
contains is set per document with ``extra_designs.<document>.models`` in the config.

To add a model: write its render function, add a :class:`Model` to :data:`MODELS`, and add
its name to ``kingmadoc.config.DOCUMENT_MODELS`` (checked when this module is imported).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

import yaml

from kingmadoc.config import DOCUMENT_MODELS
from kingmadoc.diagrams.base import DiagramBackend
from kingmadoc.exceptions import GenerationError
from kingmadoc.plan.dependencies import collapse
from kingmadoc.threats.knowledge_base import load_knowledge_base
from kingmadoc.threats.model import generate_threats, parse_threat_model
from kingmadoc.threats.report import render_diagram, render_report

if TYPE_CHECKING:
    from kingmadoc.plan.generator import PlanContext


@dataclass(frozen=True)
class Model:
    """One design model.

    Attributes:
        name: Value in ``extra_designs.<document>.models``.
        document: The extra design document it belongs to.
        title: Section heading.
        render: Returns the section body (Markdown, without the heading); ``None`` when
            the document's template renders it (it checks ``name in models``).
    """

    name: str
    document: str
    title: str
    render: Callable[[PlanContext, DiagramBackend], str] | None = None


# Detected technologies that make the first container a web application (XSS, CSRF …).
WEB_STACK = frozenset({
    "Django", "Flask", "FastAPI", "Express", "Next.js", "NestJS", "React", "Vue", "Angular",
    "Svelte", "Gin", "Echo", "Fiber",
})
# Detected data stores -> the knowledge base's data store type.
STORE_TYPES: Mapping[str, str] = MappingProxyType({
    "PostgreSQL": "SQL Database", "MySQL": "SQL Database", "MariaDB": "SQL Database",
    "SQLite": "SQL Database", "MongoDB": "Non Relational Database",
    "Elasticsearch": "Non Relational Database", "Redis": "Cache",
})


def inferred_threat_model(context: PlanContext) -> dict[str, object]:
    """A first data flow diagram from the analysis, in ``kingmadoc threats`` form."""
    from kingmadoc.plan.generator import infer_containers  # avoid import cycle

    report = context.codebase_report
    containers = [c["name"] for c in infer_containers(report, context.project_name)]
    stores = [t for t in report.detected_stack if t in STORE_TYPES]
    web = bool(WEB_STACK & set(report.detected_stack))
    elements = [
        {"name": "User", "type": "Human User"},
        *({"name": name, "type": "Web Application" if web and i == 0 else "Generic Process"}
          for i, name in enumerate(containers)),
        *({"name": store, "type": STORE_TYPES[store]} for store in stores),
    ]
    flows = [
        {"name": "Request", "from": "User", "to": containers[0], "type": "HTTPS"},
        *({"name": f"Query {store}", "from": containers[0], "to": store, "type": "Binary"}
          for store in stores),
    ]
    return {
        "title": context.feature_summary.rstrip("."),
        "elements": elements,
        "boundaries": [{"name": "Internet Boundary", "type": "Internet Boundary",
                        "contains": [*containers, *stores]}],
        "flows": flows,
    }


def _threat_model(context: PlanContext, backend: DiagramBackend) -> str:
    kb = load_knowledge_base()
    source = inferred_threat_model(context)
    model = parse_threat_model(source, kb)
    report = render_report(model, generate_threats(model, kb), kb)
    source_yaml = yaml.safe_dump(source, sort_keys=False, allow_unicode=True).strip()
    return f"""Follows the Microsoft Threat Modeling Tool: a data flow diagram with trust
boundaries, and the threats Microsoft's knowledge base generates for each interaction.
_(inferred)_ The diagram below is a first guess from the analysis: _TODO: add the real
flows and external systems in the source at the end, then run `kingmadoc threats` on it
(or model it in the tool and save the `.tm7` next to this doc)._ For each threat, set the
state, priority and justification (the **SM-n** that stops it); the evil user stories of
the functional design (**EUS-n.m**) go under the interaction they misuse.

{render_diagram(model, kb, context.diagram_format)}

{report}

### Security measures

| ID | Measure | Stops | Test |
|---|---|---|---|
| SM-1 | _TODO: e.g. at most 5 logins per minute per account_ | _TODO: #, EUS-n.m_ | _TODO_ |

<details>
<summary>Threat model source (<code>kingmadoc threats &lt;file&gt;</code>)</summary>

```yaml
{source_yaml}
```

</details>"""


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


# More nodes than this makes a dependency diagram unreadable; merge into packages instead.
MAX_GRAPH_NODES = 25


def _dependency_graph(context: PlanContext, backend: DiagramBackend) -> str:
    edges = context.codebase_report.module_dependencies or ()
    if not edges:
        return (
            "_(inferred)_ No imports between the project's own Python modules were found "
            "(only Python is analyzed so far)."
        )
    shown, depth = collapse(edges, MAX_GRAPH_NODES)
    nodes = sorted({name for edge in shown for name in edge})
    diagram = backend.render_class(
        "Module dependencies",
        [{"name": name} for name in nodes],
        [(importer, imported, "dependency", "") for importer, imported in shown],
    )
    merged = (
        f" Modules are merged into their packages (first {depth} name parts) to keep at most "
        f"{MAX_GRAPH_NODES} nodes."
        if depth
        else ""
    )
    return f"""_(inferred)_ Imports between the project's own Python modules; an arrow points
from the importing module to the imported one.{merged} Check which of these modules this
feature changes, and whether it adds new dependencies.

{diagram}"""


MODELS: tuple[Model, ...] = (
    # The functional design's template renders these itself, woven into one red thread.
    Model("user_stories", "functional_design", "User stories"),
    Model("use_case_diagram", "functional_design", "Use case diagram"),
    Model("use_cases", "functional_design", "Use case (per user story)"),
    Model("screen_designs", "functional_design", "Screen design (per user story)"),
    Model("evil_user_stories", "functional_design", "Evil user stories (per user story)"),
    Model("user_flows", "functional_design", "User flows"),
    # The technical design's template renders these between its fixed sections.
    Model("business_rules", "technical_design", "Business rules"),
    Model("permissions", "technical_design", "Permissions and roles"),
    Model("edge_cases", "technical_design", "Edge cases"),
    Model("domain_model", "domain_design", "Domain model", _domain_model),
    Model("event_storming", "domain_design", "Event storming", _event_storming),
    Model("threat_model", "technical_design", "Threat model", _threat_model),
    Model("dependency_graph", "technical_design", "Dependency graph", _dependency_graph),
    Model("threat_model", "security_design", "Threat model", _threat_model),
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
        One ``## Title`` section per selected model the template does not render itself.

    Raises:
        GenerationError: If a name is not a model of ``document``.
    """
    by_name = {m.name: m for m in MODELS if m.document == document}
    sections = []
    for name in names:
        model = by_name.get(name)
        if model is None:
            raise GenerationError(f"Unknown model {name!r} for {document}")
        if model.render is None:
            continue
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
