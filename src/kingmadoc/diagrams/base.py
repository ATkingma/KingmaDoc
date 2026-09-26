"""Diagram backend interface and the backend-neutral diagram model (pure).

Every backend (``mermaid``, ``plantuml``, ``d2``) is a module that satisfies
:class:`DiagramBackend`. Backends share the ``build_*`` functions below, which
validate the input, assign unique aliases and resolve relationships into a
:class:`Diagram`; each backend only turns that model into its own syntax.

Input conventions (plain mappings and tuples, so callers need no imports):

- Elements: ``{"name": ..., "tech": ..., "description": ...}``; only ``name`` is required.
- Relationships: ``(source_name, target_name, label)``.
- Classes: ``{"name": ..., "attributes": ["+id: int"], "methods": ["+login(pw: str): bool"]}``.
- Class relationships: ``(source_name, target_name, kind, label)``, ``kind`` in
  :data:`CLASS_RELATION_KINDS` (``inherits`` means *source inherits from target*).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from kingmadoc.exceptions import DiagramError

Element = Mapping[str, str]
Rel = tuple[str, str, str]
ClassSpec = Mapping[str, Any]
ClassRel = tuple[str, str, str, str]

CLASS_RELATION_KINDS: frozenset[str] = frozenset(
    {"inherits", "composition", "aggregation", "association", "dependency"}
)


@dataclass(frozen=True)
class Node:
    """One element of a diagram, with a unique alias.

    Attributes:
        alias: Identifier, unique within the diagram (``[a-z0-9_]``).
        label: Display name.
        kind: ``person``, ``system``, ``system_ext``, ``container``, ``component``,
            ``participant`` or ``class``.
        technology: Technology label (containers and components).
        description: Short description.
        attributes: Class attributes, e.g. ``"+id: int"``.
        methods: Class methods, e.g. ``"+login(pw: str): bool"``.
    """

    alias: str
    label: str
    kind: str
    technology: str = ""
    description: str = ""
    attributes: tuple[str, ...] = ()
    methods: tuple[str, ...] = ()


@dataclass(frozen=True)
class Edge:
    """A resolved relationship or message between two node aliases."""

    source: str
    target: str
    label: str
    kind: str = ""


@dataclass(frozen=True)
class Diagram:
    """A backend-neutral diagram.

    Attributes:
        kind: ``context``, ``container``, ``component``, ``sequence`` or ``class``.
        title: Diagram title.
        nodes: Elements outside any boundary, in input order.
        boundary: The system (container diagram) or container (component diagram)
            whose ``children`` are drawn inside it; ``None`` for other kinds.
        children: Elements inside ``boundary``.
        edges: Relationships (or messages, in order, for sequence diagrams).
    """

    kind: str
    title: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    boundary: Node | None = None
    children: tuple[Node, ...] = ()

    def parent_of(self, alias: str) -> Node | None:
        """Return the boundary if ``alias`` is drawn inside it, else ``None``."""
        if self.boundary and any(c.alias == alias for c in self.children):
            return self.boundary
        return None


@runtime_checkable
class DiagramBackend(Protocol):
    """A diagram syntax. Implemented by the modules in :mod:`kingmadoc.diagrams`.

    Each ``render_*`` returns a complete fenced Markdown code block in the backend's
    language, and raises :class:`~kingmadoc.exceptions.DiagramError` on invalid input.
    """

    #: Display name used in document headings, e.g. ``"Mermaid"``.
    LABEL: str

    def render_context(
        self,
        system_name: str,
        external_actors: Sequence[Element],
        external_systems: Sequence[Element],
        relationships: Sequence[Rel] | None = None,
        system_description: str = "",
    ) -> str:
        """C4 Context: the system, the people who use it, and external systems."""
        ...

    def render_container(
        self,
        system_name: str,
        containers: Sequence[Element],
        relationships: Sequence[Rel] = (),
        external_actors: Sequence[Element] = (),
    ) -> str:
        """C4 Container: the runnable units inside the system boundary."""
        ...

    def render_component(
        self,
        container_name: str,
        components: Sequence[Element],
        relationships: Sequence[Rel] = (),
    ) -> str:
        """C4 Component: the components inside one container."""
        ...

    def render_sequence(
        self, title: str, participants: Sequence[Element], messages: Sequence[Rel]
    ) -> str:
        """Sequence diagram: ``messages`` in order, between ``participants``."""
        ...

    def render_class(
        self, title: str, classes: Sequence[ClassSpec], relationships: Sequence[ClassRel] = ()
    ) -> str:
        """Class diagram: classes with members, and their relationships."""
        ...


def build_context(
    system_name: str,
    external_actors: Sequence[Element],
    external_systems: Sequence[Element],
    relationships: Sequence[Rel] | None = None,
    system_description: str = "",
) -> Diagram:
    """Model a C4 Context diagram (see :meth:`DiagramBackend.render_context`).

    Args:
        system_name: The system being documented.
        external_actors: People who use the system (``name``, ``description``).
        external_systems: Systems it depends on (``name``, ``description``).
        relationships: ``(source, target, label)`` by name. ``None`` means every actor
            ``"Uses"`` the system and the system ``"Uses"`` every external system.
        system_description: Optional description on the system box.

    Returns:
        The diagram model.

    Raises:
        DiagramError: If an element has no name or a relationship names an unknown element.
    """
    aliases: dict[str, str] = {}
    system = Node(register(aliases, system_name), system_name, "system", "", system_description)
    actors = [_node(aliases, a, "person") for a in external_actors]
    externals = [_node(aliases, s, "system_ext") for s in external_systems]
    if relationships is None:
        relationships = [(a["name"], system_name, "Uses") for a in external_actors] + [
            (system_name, s["name"], "Uses") for s in external_systems
        ]
    return Diagram(
        kind="context",
        title=f"System Context: {system_name}",
        nodes=(*actors, system, *externals),
        edges=_edges(relationships, aliases),
    )


def build_container(
    system_name: str,
    containers: Sequence[Element],
    relationships: Sequence[Rel] = (),
    external_actors: Sequence[Element] = (),
) -> Diagram:
    """Model a C4 Container diagram (see :meth:`DiagramBackend.render_container`).

    Args:
        system_name: The system whose boundary holds the containers.
        containers: ``name``, ``tech``, ``description``.
        relationships: ``(source, target, label)`` by name.
        external_actors: People drawn outside the boundary.

    Returns:
        The diagram model.

    Raises:
        DiagramError: If an element has no name or a relationship names an unknown element.
    """
    aliases: dict[str, str] = {}
    boundary = Node(register(aliases, f"{system_name} boundary", referable=False), system_name,
                    "system")
    actors = tuple(_node(aliases, a, "person") for a in external_actors)
    children = tuple(_node(aliases, c, "container") for c in containers)
    return Diagram(
        kind="container",
        title=f"Containers: {system_name}",
        nodes=actors,
        boundary=boundary,
        children=children,
        edges=_edges(relationships, aliases),
    )


def build_component(
    container_name: str,
    components: Sequence[Element],
    relationships: Sequence[Rel] = (),
) -> Diagram:
    """Model a C4 Component diagram (see :meth:`DiagramBackend.render_component`).

    Args:
        container_name: The container whose boundary holds the components.
        components: ``name``, ``tech``, ``description``.
        relationships: ``(source, target, label)`` by name.

    Returns:
        The diagram model.

    Raises:
        DiagramError: If an element has no name or a relationship names an unknown element.
    """
    aliases: dict[str, str] = {}
    boundary = Node(register(aliases, f"{container_name} boundary", referable=False),
                    container_name, "container")
    children = tuple(_node(aliases, c, "component") for c in components)
    return Diagram(
        kind="component",
        title=f"Components: {container_name}",
        nodes=(),
        boundary=boundary,
        children=children,
        edges=_edges(relationships, aliases),
    )


def build_sequence(
    title: str, participants: Sequence[Element], messages: Sequence[Rel]
) -> Diagram:
    """Model a sequence diagram (see :meth:`DiagramBackend.render_sequence`).

    Args:
        title: Diagram title.
        participants: ``name``, ``description``; drawn left to right in this order.
        messages: ``(sender, receiver, text)`` by participant name, in time order.

    Returns:
        The diagram model.

    Raises:
        DiagramError: If a participant has no name or a message names an unknown one.
    """
    aliases: dict[str, str] = {}
    nodes = tuple(_node(aliases, p, "participant") for p in participants)
    return Diagram(kind="sequence", title=title, nodes=nodes, edges=_edges(messages, aliases))


def build_class(
    title: str, classes: Sequence[ClassSpec], relationships: Sequence[ClassRel] = ()
) -> Diagram:
    """Model a class diagram (see :meth:`DiagramBackend.render_class`).

    Args:
        title: Diagram title.
        classes: ``name``, optional ``attributes`` and ``methods`` (lists of strings).
        relationships: ``(source, target, kind, label)`` by class name.

    Returns:
        The diagram model.

    Raises:
        DiagramError: On a missing name, non-string members, an unknown class in a
            relationship, or an unknown relationship kind.
    """
    aliases: dict[str, str] = {}
    nodes = []
    for spec in classes:
        name = element_name(spec)
        nodes.append(
            Node(
                register(aliases, name),
                name,
                "class",
                attributes=_members(spec, "attributes"),
                methods=_members(spec, "methods"),
            )
        )
    edges = []
    for source, target, kind, label in relationships:
        if kind not in CLASS_RELATION_KINDS:
            raise DiagramError(
                f"Unknown class relationship {kind!r}; use one of "
                f"{', '.join(sorted(CLASS_RELATION_KINDS))}"
            )
        edges.append(Edge(lookup(aliases, source), lookup(aliases, target), label, kind))
    return Diagram(kind="class", title=title, nodes=tuple(nodes), edges=tuple(edges))


def make_alias(text: str) -> str:
    """Turn arbitrary text into a diagram identifier.

    Args:
        text: Any label.

    Returns:
        A lowercase identifier of word characters, never starting with a digit.

    Example:
        >>> make_alias("Web App (v2)")
        'web_app_v2'
    """
    alias = re.sub(r"\W+", "_", text.strip().lower()).strip("_") or "element"
    return f"_{alias}" if alias[0].isdigit() else alias


def register(aliases: dict[str, str], name: str, *, referable: bool = True) -> str:
    """Give ``name`` a unique alias within one diagram; ``aliases`` maps name -> alias.

    Non-referable entries (boundaries) only reserve their alias: relationships
    cannot target them, so a container may share the system's name.

    Args:
        aliases: The diagram's alias table (updated in place).
        name: Element name.
        referable: Whether relationships may refer to ``name``.

    Returns:
        The new alias (``name``'s alias, suffixed ``_2``, ``_3`` … on collisions).
    """
    base = alias = make_alias(name)
    taken = set(aliases.values())
    n = 2
    while alias in taken:
        alias, n = f"{base}_{n}", n + 1
    # NUL cannot appear in a real element name, so reserved keys never match a lookup.
    aliases.setdefault(name if referable else f"\0{alias}", alias)
    return alias


def lookup(aliases: Mapping[str, str], name: str) -> str:
    """Return the alias of ``name``.

    Args:
        aliases: The diagram's alias table.
        name: Element name used in a relationship.

    Returns:
        The alias.

    Raises:
        DiagramError: If no element has that name.
    """
    try:
        return aliases[name]
    except KeyError:
        raise DiagramError(f"Relationship refers to unknown element {name!r}") from None


def element_name(element: Mapping[str, Any]) -> str:
    """Return an element's required ``name``.

    Args:
        element: Element mapping.

    Returns:
        The name.

    Raises:
        DiagramError: If the name is missing or blank.
    """
    name = element.get("name")
    if not isinstance(name, str) or not name.strip():
        raise DiagramError(f"Diagram element without a name: {dict(element)!r}")
    return name


def one_line(text: str) -> str:
    """Collapse all whitespace (including newlines, which end statements) to single spaces.

    Args:
        text: Any text.

    Returns:
        The text on one line.
    """
    return " ".join(text.split())


def fence(language: str, lines: Sequence[str]) -> str:
    """Wrap diagram source in a fenced Markdown code block.

    Args:
        language: Code block language, e.g. ``"mermaid"``.
        lines: Diagram source lines.

    Returns:
        The fenced block (no trailing newline).
    """
    return f"```{language}\n" + "\n".join(lines) + "\n```"


def split_member(member: str) -> tuple[str, str]:
    """Split a class member into ``(signature, type)``.

    Args:
        member: ``"+id: int"``, ``"+login(pw: str): bool"`` or just ``"+id"``.

    Returns:
        ``("+id", "int")``, ``("+login(pw: str)", "bool")`` or ``("+id", "")``.

    Example:
        >>> split_member("+login(pw: str): bool")
        ('+login(pw: str)', 'bool')
    """
    member = one_line(member)
    if ")" in member:
        end = member.rindex(")") + 1
        return member[:end], member[end:].lstrip(" :")
    signature, _, typ = member.partition(":")
    return signature.strip(), typ.strip()


def _node(aliases: dict[str, str], element: Element, kind: str) -> Node:
    name = element_name(element)
    return Node(
        register(aliases, name),
        name,
        kind,
        element.get("tech", ""),
        element.get("description", ""),
    )


def _edges(relationships: Sequence[Rel], aliases: Mapping[str, str]) -> tuple[Edge, ...]:
    return tuple(
        Edge(lookup(aliases, source), lookup(aliases, target), label)
        for source, target, label in relationships
    )


def _members(spec: ClassSpec, key: str) -> tuple[str, ...]:
    value = spec.get(key, ())
    if isinstance(value, str) or not all(isinstance(m, str) for m in value):
        raise DiagramError(f"Class {spec.get('name')!r}: {key} must be a list of strings")
    return tuple(one_line(m) for m in value)
