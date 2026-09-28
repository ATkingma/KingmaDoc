"""A data flow diagram and the threats the knowledge base generates for it."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from kingmadoc.exceptions import ThreatModelError
from kingmadoc.threats.filters import Subject, matches
from kingmadoc.threats.knowledge_base import KnowledgeBase

# The tool's threat states, in its report's order; generated threats start "Not Started".
STATES: tuple[str, ...] = (
    "Not Started", "Not Applicable", "Needs Investigation", "Mitigation Implemented",
)
PRIORITIES: tuple[str, ...] = ("High", "Medium", "Low")
# The tool gives every generated threat this priority until someone changes it.
DEFAULT_PRIORITY = "High"
GENERIC_KINDS: Mapping[str, str] = MappingProxyType(
    {"GE.P": "Process", "GE.EI": "External Interactor", "GE.DS": "Data Store"}
)


def _properties(raw: Any, where: str) -> Mapping[str, str]:
    if raw is None:
        return MappingProxyType({})
    if not isinstance(raw, Mapping):
        raise ThreatModelError(f"{where}: properties must be a mapping")
    return MappingProxyType({str(k): str(v) for k, v in raw.items()})


@dataclass(frozen=True)
class Element:
    """A process, external interactor or data store."""

    name: str
    type_id: str
    properties: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class Boundary:
    """A trust boundary around the elements it contains (the other side is outside)."""

    name: str
    type_id: str
    contains: tuple[str, ...]


@dataclass(frozen=True)
class Flow:
    """A one-way data flow between two elements."""

    name: str
    source: str
    target: str
    type_id: str
    properties: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class ThreatModel:
    """A data flow diagram in the tool's terms."""

    title: str
    elements: tuple[Element, ...]
    boundaries: tuple[Boundary, ...]
    flows: tuple[Flow, ...]


@dataclass(frozen=True)
class Threat:
    """One generated threat on one interaction (data flow)."""

    number: int
    type_id: str
    flow: Flow
    category: str
    title: str
    description: str
    state: str = STATES[0]
    priority: str = DEFAULT_PRIORITY
    justification: str = ""


def _typed(kb: KnowledgeBase, name: str, generic: str, where: str) -> str:
    element_type = kb.element_type(name)
    if generic not in kb.ancestors(element_type.id):
        raise ThreatModelError(f"{where}: {name!r} is not a {kb.elements[generic].name}")
    return element_type.id


def parse_threat_model(data: Mapping[str, Any], kb: KnowledgeBase) -> ThreatModel:
    """Build a threat model from its YAML/JSON form.

    ``elements`` (``name``, ``type``, optional ``properties``), ``boundaries`` (``name``,
    optional ``type``, default Internet Boundary, and ``contains``: element names) and
    ``flows`` (``name``, ``from``, ``to``, optional ``type``, default HTTPS, and
    ``properties``). Types are the tool's names ("Web Application") or IDs.

    Raises:
        ThreatModelError: On unknown types, duplicate names or flows between unknown
            elements.
    """
    elements: list[Element] = []
    for raw in data.get("elements") or []:
        name = str(raw.get("name", "")).strip()
        type_id = kb.element_type(str(raw.get("type", "Generic Process"))).id
        if not name or not any(g in kb.ancestors(type_id) for g in GENERIC_KINDS):
            raise ThreatModelError(f"Element {raw!r} needs a name and a process, "
                                   "external interactor or data store type")
        elements.append(Element(name, type_id, _properties(raw.get("properties"), name)))
    names = [e.name for e in elements]
    if len(set(names)) != len(names):
        raise ThreatModelError("Element names must be unique")
    boundaries = []
    for raw in data.get("boundaries") or []:
        name = str(raw.get("name", "Internet Boundary"))
        type_id = str(raw.get("type", "Internet Boundary"))
        found = kb.element_type(type_id).id
        if not {"GE.TB.L", "GE.TB.B"} & set(kb.ancestors(found)):
            raise ThreatModelError(f"Boundary {name!r}: {type_id!r} is not a trust boundary")
        contains = tuple(str(n) for n in raw.get("contains") or [])
        unknown = [n for n in contains if n not in names]
        if unknown:
            raise ThreatModelError(f"Boundary {name!r} contains unknown elements {unknown}")
        boundaries.append(Boundary(name, found, contains))
    flows = []
    for raw in data.get("flows") or []:
        source, target = str(raw.get("from", "")), str(raw.get("to", ""))
        if source not in names or target not in names or source == target:
            raise ThreatModelError(f"Flow {raw!r} must connect two different known elements")
        name = str(raw.get("name") or f"{source} to {target}")
        type_id = _typed(kb, str(raw.get("type", "HTTPS")), "GE.DF", name)
        flows.append(Flow(name, source, target, type_id, _properties(raw.get("properties"), name)))
    return ThreatModel(str(data.get("title", "Threat model")), tuple(elements),
                       tuple(boundaries), tuple(flows))


def crossed(model: ThreatModel, flow: Flow) -> tuple[Boundary, ...]:
    """The trust boundaries a flow crosses: exactly one of its ends is inside."""
    return tuple(b for b in model.boundaries
                 if (flow.source in b.contains) != (flow.target in b.contains))


_PLACEHOLDER = re.compile(r"\{(source|target|flow)\.name\}", re.IGNORECASE)


def _fill(text: str, names: Mapping[str, str]) -> str:
    return _PLACEHOLDER.sub(lambda m: names[m.group(1).lower()], text)


def generate_threats(model: ThreatModel, kb: KnowledgeBase) -> tuple[Threat, ...]:
    """Every threat the knowledge base generates, per flow, numbered like the tool's report.

    Raises:
        ThreatModelError: If a filter in the knowledge base cannot be read.
    """
    by_name = {e.name: e for e in model.elements}
    threats: list[Threat] = []
    for flow in model.flows:
        source, target = by_name[flow.source], by_name[flow.target]
        crossing = frozenset(t for b in crossed(model, flow) for t in kb.ancestors(b.type_id))
        subject = Subject(
            types={"source": kb.ancestors(source.type_id), "target": kb.ancestors(target.type_id),
                   "flow": kb.ancestors(flow.type_id)},
            properties={"source": source.properties, "target": target.properties,
                        "flow": flow.properties},
            crosses=crossing,
            default=kb.default,
        )
        names = {"source": source.name, "target": target.name, "flow": flow.name}
        for threat_type in kb.threats:
            if not matches(threat_type.include, subject):
                continue
            if threat_type.exclude and matches(threat_type.exclude, subject):
                continue
            threats.append(Threat(
                number=len(threats) + 1,
                type_id=threat_type.id,
                flow=flow,
                category=kb.categories.get(threat_type.category, threat_type.category),
                title=_fill(threat_type.title, names),
                description=_fill(threat_type.description, names),
            ))
    return tuple(threats)


def state_counts(threats: Sequence[Threat]) -> dict[str, int]:
    """Threats per state, in the order of :data:`STATES`."""
    return {state: sum(t.state == state for t in threats) for state in STATES}
