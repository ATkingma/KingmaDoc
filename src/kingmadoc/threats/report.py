"""Render a threat model like the Threat Modeling Tool's Full Report (Markdown + D2)."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType

from kingmadoc.threats.knowledge_base import KnowledgeBase
from kingmadoc.threats.model import GENERIC_KINDS, Threat, ThreatModel, state_counts


def _q(text: str) -> str:
    """A double-quoted D2 label."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
    return '"' + " ".join(escaped.split()) + '"'


def _cell(text: str) -> str:
    """Text that is safe inside a Markdown table cell."""
    return " ".join(text.split()).replace("|", "\\|")


def kind(kb: KnowledgeBase, type_id: str) -> str:
    """The generic kind of an element type: Process, External Interactor or Data Store."""
    return next(GENERIC_KINDS[t] for t in kb.ancestors(type_id) if t in GENERIC_KINDS)


def _layout(model: ThreatModel, kb: KnowledgeBase) -> tuple[dict[str, str], dict[str, str]]:
    """Element name -> diagram ID, and element name -> ID of the boundary it sits in."""
    ids = {e.name: f"e{i}" for i, e in enumerate(model.elements, 1)}
    inside = {name: f"b{i}" for i, b in enumerate(model.boundaries, 1) for name in b.contains}
    return ids, inside


def _shape(kb: KnowledgeBase, type_id: str) -> str:
    """person, process, store or interactor."""
    if type_id == "SE.EI.TMCore.User":
        return "person"
    return {"Process": "process", "Data Store": "store"}.get(kind(kb, type_id), "interactor")


def _flow_label(kb: KnowledgeBase, name: str, type_id: str) -> str:
    return f"{name} [{kb.elements[type_id].name}]"


def render_d2(model: ThreatModel, kb: KnowledgeBase) -> str:
    """The data flow diagram in the tool's notation, as a fenced D2 block.

    External interactors are rectangles (a human user a person), processes circles, data
    stores ``stored_data``; boundaries dashed red boxes; flows labelled with name and type.
    """
    ids, inside = _layout(model, kb)
    shapes = {"person": "person", "process": "circle", "store": "stored_data",
              "interactor": "rectangle"}

    def node(element_name: str, indent: str) -> str:
        element = next(e for e in model.elements if e.name == element_name)
        shape = shapes[_shape(kb, element.type_id)]
        return f"{indent}{ids[element.name]}: {_q(element.name)} {{shape: {shape}}}"

    lines = [
        f"title: {_q('[Threat model] ' + model.title)} "
        "{shape: text; near: top-center; style: {font-size: 24; bold: true}}",
        "direction: right",
        "vars: {",
        "  d2-legend: {",
        "    e: External Interactor",
        "    p: Process {shape: circle}",
        "    s: Data Store {shape: stored_data}",
        "    t: Trust Boundary {style: {stroke: red; stroke-dash: 4; fill: transparent}}",
        "  }",
        "}",
    ]
    lines += [node(e.name, "") for e in model.elements if e.name not in inside]
    for index, boundary in enumerate(model.boundaries, 1):
        lines.append(f"b{index}: {_q(boundary.name)} {{")
        lines.append("  style: {stroke: red; stroke-dash: 4; fill: transparent}")
        lines += [node(name, "  ") for name in boundary.contains if inside[name] == f"b{index}"]
        lines.append("}")

    def path(name: str) -> str:
        return f"{inside[name]}.{ids[name]}" if name in inside else ids[name]

    for flow in model.flows:
        label = _flow_label(kb, flow.name, flow.type_id)
        lines.append(f"{path(flow.source)} -> {path(flow.target)}: {_q(label)}")
    return "```d2\n" + "\n".join(lines) + "\n```"


def render_mermaid(model: ThreatModel, kb: KnowledgeBase) -> str:
    """The data flow diagram as a Mermaid flowchart (circles, cylinders, dashed red boxes)."""
    ids, inside = _layout(model, kb)

    def q(text: str) -> str:
        return '"' + " ".join(text.split()).replace('"', "#quot;") + '"'

    brackets = {"person": ("[", "]"), "interactor": ("[", "]"), "process": ("((", "))"),
                "store": ("[(", ")]")}

    def node(element_name: str, indent: str) -> str:
        element = next(e for e in model.elements if e.name == element_name)
        left, right = brackets[_shape(kb, element.type_id)]
        return f"{indent}{ids[element.name]}{left}{q(element.name)}{right}"

    lines = ["flowchart LR"]
    lines += [node(e.name, "    ") for e in model.elements if e.name not in inside]
    for index, boundary in enumerate(model.boundaries, 1):
        lines.append(f"    subgraph b{index}[{q(boundary.name)}]")
        lines += [node(n, "        ") for n in boundary.contains if inside[n] == f"b{index}"]
        lines.append("    end")
    lines += [f"    {ids[f.source]} -- {q(_flow_label(kb, f.name, f.type_id))} --> {ids[f.target]}"
              for f in model.flows]
    lines += [f"    style b{i} fill:none,stroke:#e00,stroke-dasharray:5 5"
              for i in range(1, len(model.boundaries) + 1)]
    return "```mermaid\n" + "\n".join(lines) + "\n```"


def render_plantuml(model: ThreatModel, kb: KnowledgeBase) -> str:
    """The data flow diagram in PlantUML (ellipse processes, databases, dashed red boxes)."""
    ids, inside = _layout(model, kb)

    def q(text: str) -> str:
        return '"' + " ".join(text.split()).replace('"', "<U+0022>") + '"'

    keywords = {"person": "actor", "interactor": "rectangle", "process": "usecase",
                "store": "database"}

    def node(element_name: str, indent: str) -> str:
        element = next(e for e in model.elements if e.name == element_name)
        keyword = keywords[_shape(kb, element.type_id)]
        return f"{indent}{keyword} {q(element.name)} as {ids[element.name]}"

    lines = ["@startuml", "left to right direction"]
    lines += [node(e.name, "") for e in model.elements if e.name not in inside]
    for index, boundary in enumerate(model.boundaries, 1):
        lines.append(f"rectangle {q(boundary.name)} as b{index} #line.dashed;line:red {{")
        lines += [node(n, "  ") for n in boundary.contains if inside[n] == f"b{index}"]
        lines.append("}")
    lines += [f"{ids[f.source]} --> {ids[f.target]} : {q(_flow_label(kb, f.name, f.type_id))}"
              for f in model.flows]
    lines.append("@enduml")
    return "```plantuml\n" + "\n".join(lines) + "\n```"


DIAGRAM_RENDERERS: Mapping[str, Callable[[ThreatModel, KnowledgeBase], str]] = MappingProxyType(
    {"d2": render_d2, "mermaid": render_mermaid, "plantuml": render_plantuml}
)


def render_diagram(model: ThreatModel, kb: KnowledgeBase, diagram_format: str = "d2") -> str:
    """The data flow diagram in ``d2`` (default), ``mermaid`` or ``plantuml``."""
    return DIAGRAM_RENDERERS[diagram_format](model, kb)


def render_report(
    model: ThreatModel, threats: Sequence[Threat], kb: KnowledgeBase, heading: str = "###"
) -> str:
    """The report: elements, the state summary and one threat table per interaction.

    Args:
        model: The data flow diagram.
        threats: From :func:`kingmadoc.threats.model.generate_threats`.
        kb: The knowledge base (for stencil names).
        heading: Markdown level of the "Interaction" headings.
    """
    boundary_of = {name: b.name for b in model.boundaries for name in b.contains}
    elements = "\n".join(
        f"| {_cell(e.name)} | {kb.elements[e.type_id].name} ({kind(kb, e.type_id)}) | "
        f"{_cell(boundary_of.get(e.name, 'outside'))} |"
        for e in model.elements
    )
    counts = state_counts(threats)
    parts = [
        "| Element | Stencil | Trust boundary |\n|---|---|---|\n" + elements,
        "| " + " | ".join(counts) + " | Total |\n|" + "---|" * (len(counts) + 1) + "\n| "
        + " | ".join(str(c) for c in counts.values()) + f" | {len(threats)} |",
    ]
    for flow in model.flows:
        rows = [t for t in threats if t.flow == flow]
        if not rows:
            continue
        table = "\n".join(
            f"| {t.number} | {_cell(t.title)} | {t.category} | {_cell(t.description)} | "
            f"{t.state} | {t.priority} | {_cell(t.justification) or '_TODO_'} |"
            for t in rows
        )
        parts.append(
            f"{heading} Interaction: {_cell(flow.name)} ({_cell(flow.source)} → "
            f"{_cell(flow.target)})\n\n"
            "| # | Threat | Category | Description | State | Priority | Justification |\n"
            "|---|---|---|---|---|---|---|\n" + table
        )
    parts.append(
        f"_Threats generated from Microsoft's {kb.name} {kb.version} "
        f"([source]({kb.url}), MIT license), as the Threat Modeling Tool does._"
    )
    return "\n\n".join(parts)


def catalog_markdown(kb: KnowledgeBase) -> str:
    """The knowledge base as a Markdown reference, for agents that cannot run the CLI."""
    groups: dict[str, list[str]] = {}
    for type_id, element in kb.elements.items():
        ancestors = kb.ancestors(type_id)
        group = next(
            (label for generic, label in (("GE.P", "Process"), ("GE.EI", "External Interactor"),
                                          ("GE.DS", "Data Store"), ("GE.DF", "Data Flow"),
                                          ("GE.TB.L", "Trust Boundary"),
                                          ("GE.TB.B", "Trust Boundary"))
             if generic in ancestors),
            "Other",
        )
        groups.setdefault(group, []).append(f"{element.name} (`{type_id}`)")
    stencils = "\n".join(f"| {group} | {', '.join(names)} |" for group, names in groups.items())
    used = sorted({m.lower() for t in kb.threats
                   for m in re.findall(r"\.([\w-]+) is", f"{t.include} {t.exclude}")})
    defaults = "\n".join(
        f"| {element.name} | "
        + ", ".join(f"{name} = {values[0]}" for name, values in element.attributes.items()
                    if name.lower() in used and values)
        + " |"
        for element in kb.elements.values()
        if any(name.lower() in used and values for name, values in element.attributes.items())
    )
    rows = "\n".join(
        f"| {t.id} | {kb.categories.get(t.category, t.category)} | {_cell(t.title)} | "
        f"`{_cell(t.include)}` | {f'`{_cell(t.exclude)}`' if t.exclude else '—'} | "
        f"{_cell(t.description)} |"
        for t in kb.threats
    )
    return f"""# Threat knowledge base (Microsoft Threat Modeling Tool)

Contents: Stencils · Property defaults · How a threat is generated · Threat types.

Generated from Microsoft's **{kb.name} {kb.version}**, the default template of the
Threat Modeling Tool ([source]({kb.url}), MIT license, Copyright (c) Microsoft
Corporation). Do not edit: `scripts/import_tmt_knowledge_base.py` and
`scripts/build_threat_reference.py` rebuild it. With KingmaDoc installed,
`kingmadoc threats <file>.yml` applies it for you; use this table only without it.

## Stencils

| Kind | Types (name and ID) |
| ---- | ------------------- |
{stencils}

## Property defaults

The properties the filters test, with the value a stencil has until you set another
(a standard stencil inherits what it does not list from its generic type).

| Stencil | Defaults |
| ------- | -------- |
{defaults}

## How a threat is generated

For every data flow, each threat type below applies when its **When** filter holds and
its **Not when** filter does not. `source` and `target` are the flow's ends and `flow`
the flow; `is 'GE.P'` matches the type or any type under it (a Web Application is a
`GE.P`); `flow crosses 'GE.TB.L'` means one end is inside a trust boundary and the other
is not; a property without a value has its first allowed value (HTTPS provides
confidentiality and integrity, HTTP does not). Replace `{{source.Name}}`,
`{{target.Name}}` and `{{flow.Name}}` in the title and description. Number the threats
in flow order, as the tool's report does.

## Threat types

| ID | Category | Title | When | Not when | Description |
| -- | -------- | ----- | ---- | -------- | ----------- |
{rows}
"""
