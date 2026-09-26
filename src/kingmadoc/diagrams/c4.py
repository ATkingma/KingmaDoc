"""Builders for Mermaid C4 Context and Container diagrams."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Person:
    """A human actor."""

    alias: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class ExternalSystem:
    """A system outside the one being documented."""

    alias: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class Container:
    """A deployable/runnable unit inside the system (app, service, database, ...)."""

    alias: str
    label: str
    technology: str = ""
    description: str = ""


@dataclass(frozen=True)
class Relationship:
    """A directed relationship between two elements, referenced by alias."""

    source: str
    target: str
    label: str
    technology: str = ""


def make_alias(text: str) -> str:
    """Turn arbitrary text into a valid Mermaid element identifier.

    Args:
        text: Any label.

    Returns:
        A lowercase identifier of word characters, never starting with a digit.
    """
    alias = re.sub(r"\W+", "_", text.strip().lower()).strip("_") or "element"
    return f"_{alias}" if alias[0].isdigit() else alias


def build_context_diagram(
    system_alias: str,
    system_label: str,
    system_description: str,
    people: list[Person],
    external_systems: list[ExternalSystem],
    relationships: list[Relationship],
) -> str:
    """Build a Mermaid ``C4Context`` diagram.

    Args:
        system_alias: Identifier of the system under design.
        system_label: Display name of the system.
        system_description: Short description of the system.
        people: Human actors.
        external_systems: Systems the system interacts with.
        relationships: Relationships between any of the above.

    Returns:
        Mermaid source (without code fences).
    """
    lines = ["C4Context", f"    title System Context: {_clean(system_label)}", ""]
    lines += [_element("Person", p.alias, p.label, p.description) for p in people]
    lines.append(_element("System", system_alias, system_label, system_description))
    lines += [
        _element("System_Ext", s.alias, s.label, s.description) for s in external_systems
    ]
    lines += _relationships(relationships)
    return "\n".join(lines)


def build_container_diagram(
    system_alias: str,
    system_label: str,
    people: list[Person],
    containers: list[Container],
    external_systems: list[ExternalSystem],
    relationships: list[Relationship],
) -> str:
    """Build a Mermaid ``C4Container`` diagram.

    Args:
        system_alias: Identifier used for the system boundary.
        system_label: Display name of the system.
        people: Human actors.
        containers: Containers inside the system boundary.
        external_systems: Systems outside the boundary.
        relationships: Relationships between any of the above.

    Returns:
        Mermaid source (without code fences).
    """
    lines = ["C4Container", f"    title Containers: {_clean(system_label)}", ""]
    lines += [_element("Person", p.alias, p.label, p.description) for p in people]
    lines.append(f'    System_Boundary({system_alias}, "{_clean(system_label)}") {{')
    for c in containers:
        # Extra indent: containers are nested inside the boundary block.
        lines.append(
            f'        Container({c.alias}, "{_clean(c.label)}", '
            f'"{_clean(c.technology)}", "{_clean(c.description)}")'
        )
    lines.append("    }")
    lines += [
        _element("System_Ext", s.alias, s.label, s.description) for s in external_systems
    ]
    lines += _relationships(relationships)
    return "\n".join(lines)


def _element(kind: str, alias: str, label: str, description: str) -> str:
    return f'    {kind}({alias}, "{_clean(label)}", "{_clean(description)}")'


def _relationships(relationships: list[Relationship]) -> list[str]:
    if not relationships:
        return []
    lines = [""]
    for r in relationships:
        args = f'{r.source}, {r.target}, "{_clean(r.label)}"'
        if r.technology:
            args += f', "{_clean(r.technology)}"'
        lines.append(f"    Rel({args})")
    return lines


def _clean(text: str) -> str:
    """Make text safe inside a double-quoted Mermaid string."""
    return " ".join(text.replace('"', "'").split())
