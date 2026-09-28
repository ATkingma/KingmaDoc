"""Microsoft's threat knowledge base: element types, categories and threat types."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from types import MappingProxyType

from kingmadoc.exceptions import ThreatModelError

KNOWLEDGE_BASE_FILE = "sdl_knowledge_base.json"


@dataclass(frozen=True)
class ElementType:
    """A stencil, e.g. ``SE.P.TMCore.WebApp`` ("Web Application").

    Attributes:
        id: The tool's ID; ``GE.*`` are the generic types, ``SE.*`` the standard ones.
        name: Display name.
        parent: The generic type it specialises (``None`` for a generic type).
        attributes: Property name -> allowed values; the first value is the default.
    """

    id: str
    name: str
    parent: str | None
    attributes: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class ThreatType:
    """One threat the tool generates, with its generation filters.

    Attributes:
        id: The tool's ID, e.g. ``S3``.
        category: STRIDE letter (``S``, ``T``, ``R``, ``I``, ``D``, ``E``).
        title: Title with ``{source.Name}``, ``{target.Name}``, ``{flow.Name}``.
        description: Description with the same placeholders.
        include: Filter that must hold for a data flow (the tool's syntax).
        exclude: Filter that suppresses the threat when it holds (may be empty).
    """

    id: str
    category: str
    title: str
    description: str
    include: str
    exclude: str


@dataclass(frozen=True)
class KnowledgeBase:
    """The imported knowledge base and where it comes from."""

    name: str
    version: str
    url: str
    license: str
    categories: Mapping[str, str]
    elements: Mapping[str, ElementType]
    threats: tuple[ThreatType, ...]

    def element_type(self, name_or_id: str) -> ElementType:
        """Look up an element type by its ID or display name (case-insensitive).

        Raises:
            ThreatModelError: If no element type has that ID or name.
        """
        wanted = name_or_id.strip().lower()
        for element in self.elements.values():
            if wanted in (element.id.lower(), element.name.lower()):
                return element
        raise ThreatModelError(f"Unknown element type {name_or_id!r}")

    def ancestors(self, type_id: str) -> tuple[str, ...]:
        """The type and every type it specialises, most specific first."""
        chain: list[str] = []
        current: str | None = type_id
        while current and current in self.elements:
            chain.append(current)
            current = self.elements[current].parent
        return tuple(chain)

    def default(self, type_id: str, attribute: str) -> str | None:
        """The default value of a property, inherited from the parent types."""
        for ancestor in self.ancestors(type_id):
            values = self.elements[ancestor].attributes.get(attribute)
            if values:
                return values[0]
        return None


@cache
def load_knowledge_base() -> KnowledgeBase:
    """Read the bundled knowledge base (package data, read once)."""
    raw = json.loads(
        files("kingmadoc.threats").joinpath(KNOWLEDGE_BASE_FILE).read_text(encoding="utf-8")
    )
    elements = {
        e["id"]: ElementType(
            id=e["id"],
            name=e["name"],
            parent=None if e["parent"] in (None, "ROOT") else e["parent"],
            attributes=MappingProxyType(
                {name: tuple(a["values"]) for name, a in e["attributes"].items()}
            ),
        )
        for e in raw["elements"]
    }
    return KnowledgeBase(
        name=raw["source"]["name"],
        version=raw["source"]["version"],
        url=raw["source"]["url"],
        license=raw["source"]["license"],
        categories=MappingProxyType(dict(raw["categories"])),
        elements=MappingProxyType(elements),
        threats=tuple(ThreatType(**t) for t in raw["threats"]),
    )
