"""PlantUML backend: C4 via the C4-PlantUML standard library (``!include <C4/...>``,
bundled with PlantUML), plus sequence and class diagrams.

Escaping: ``"`` inside quoted strings becomes ``<U+0022>`` (PlantUML's Unicode escape;
``&quot;`` would be shown literally). Titles and message texts are unquoted.

Example:
    >>> print(render_context("Shop", [{"name": "Customer"}], []))
    ```plantuml
    @startuml
    !include <C4/C4_Context>
    title System Context: Shop
    <BLANKLINE>
    Person(customer, "Customer")
    System(shop, "Shop")
    <BLANKLINE>
    Rel(customer, shop, "Uses")
    @enduml
    ```
"""

from __future__ import annotations

from collections.abc import Sequence
from types import MappingProxyType

from kingmadoc.diagrams.base import (
    ClassRel,
    ClassSpec,
    Diagram,
    Element,
    Node,
    Rel,
    build_class,
    build_component,
    build_container,
    build_context,
    build_sequence,
    fence,
    one_line,
)

LABEL = "PlantUML"

_C4_KEYWORDS = MappingProxyType({
    "person": "Person",
    "system": "System",
    "system_ext": "System_Ext",
    "container": "Container",
    "component": "Component",
})
_C4_LIBRARIES = MappingProxyType({
    "context": "C4/C4_Context",
    "container": "C4/C4_Container",
    "component": "C4/C4_Component",
})
_BOUNDARIES = MappingProxyType({"container": "System_Boundary", "component": "Container_Boundary"})
# Class relationship kind -> (arrow, whether source and target swap sides).
_CLASS_ARROWS = MappingProxyType({
    "inherits": ("<|--", True),
    "composition": ("*--", False),
    "aggregation": ("o--", False),
    "association": ("-->", False),
    "dependency": ("..>", False),
})


def render_context(
    system_name: str,
    external_actors: Sequence[Element],
    external_systems: Sequence[Element],
    relationships: Sequence[Rel] = (),
    system_description: str = "",
    *,
    default_relationships: bool = True,
) -> str:
    """Render a C4-PlantUML Context diagram; see :func:`kingmadoc.diagrams.base.build_context`.

    Args:
        system_name: The system being documented.
        external_actors: People who use the system.
        external_systems: Systems it depends on.
        relationships: ``(source, target, label)``, drawn after the defaults.
        system_description: Optional description on the system box.
        default_relationships: Also draw actor -> system and system -> external arrows.

    Returns:
        A fenced ``plantuml`` block.
    """
    return _c4(build_context(
        system_name,
        external_actors,
        external_systems,
        relationships,
        system_description,
        default_relationships=default_relationships,
    ))


def render_container(
    system_name: str,
    containers: Sequence[Element],
    relationships: Sequence[Rel] = (),
    external_actors: Sequence[Element] = (),
) -> str:
    """Render a C4-PlantUML Container diagram.

    Args:
        system_name: The system whose boundary holds the containers.
        containers: ``name``, ``tech``, ``description``.
        relationships: ``(source, target, label)`` by name.
        external_actors: People drawn outside the boundary.

    Returns:
        A fenced ``plantuml`` block.
    """
    return _c4(build_container(system_name, containers, relationships, external_actors))


def render_component(
    container_name: str,
    components: Sequence[Element],
    relationships: Sequence[Rel] = (),
) -> str:
    """Render a C4-PlantUML Component diagram.

    Args:
        container_name: The container whose boundary holds the components.
        components: ``name``, ``tech``, ``description``.
        relationships: ``(source, target, label)`` by name.

    Returns:
        A fenced ``plantuml`` block.
    """
    return _c4(build_component(container_name, components, relationships))


def render_sequence(
    title: str, participants: Sequence[Element], messages: Sequence[Rel]
) -> str:
    """Render a PlantUML sequence diagram.

    Args:
        title: Diagram title.
        participants: Drawn left to right in this order.
        messages: ``(sender, receiver, text)`` in time order.

    Returns:
        A fenced ``plantuml`` block.
    """
    diagram = build_sequence(title, participants, messages)
    lines = ["@startuml", f"title {one_line(diagram.title)}"]
    lines += [f'participant "{_escape(n.label)}" as {n.alias}' for n in diagram.nodes]
    lines += [f"{e.source} -> {e.target} : {one_line(e.label)}" for e in diagram.edges]
    lines.append("@enduml")
    return fence("plantuml", lines)


def render_class(
    title: str, classes: Sequence[ClassSpec], relationships: Sequence[ClassRel] = ()
) -> str:
    """Render a PlantUML class diagram.

    Args:
        title: Diagram title.
        classes: ``name``, ``attributes``, ``methods``.
        relationships: ``(source, target, kind, label)`` by class name.

    Returns:
        A fenced ``plantuml`` block.
    """
    diagram = build_class(title, classes, relationships)
    lines = ["@startuml", f"title {one_line(diagram.title)}"]
    for node in diagram.nodes:
        header = f'class "{_escape(node.label)}" as {node.alias}'
        members = [*node.attributes, *node.methods]
        if not members:
            lines.append(header)
            continue
        lines.append(header + " {")
        # Braces would close the class body early.
        lines += [f"  {m.replace('{', '(').replace('}', ')')}" for m in members]
        lines.append("}")
    for edge in diagram.edges:
        arrow, swap = _CLASS_ARROWS[edge.kind]
        left, right = (edge.target, edge.source) if swap else (edge.source, edge.target)
        label = f" : {one_line(edge.label)}" if edge.label else ""
        lines.append(f"{left} {arrow} {right}{label}")
    lines.append("@enduml")
    return fence("plantuml", lines)


def _c4(diagram: Diagram) -> str:
    lines = [
        "@startuml",
        f"!include <{_C4_LIBRARIES[diagram.kind]}>",
        f"title {one_line(diagram.title)}",
        "",
    ]
    lines += [_element(n) for n in diagram.nodes]
    if diagram.boundary is not None:
        b = diagram.boundary
        lines.append(f'{_BOUNDARIES[diagram.kind]}({b.alias}, "{_escape(b.label)}") {{')
        lines += [
            f'    {_C4_KEYWORDS[c.kind]}({c.alias}, "{_escape(c.label)}", '
            f'"{_escape(c.technology)}", "{_escape(c.description)}")'
            for c in diagram.children
        ]
        lines.append("}")
    if diagram.edges:
        lines.append("")
        lines += [f'Rel({e.source}, {e.target}, "{_escape(e.label)}")' for e in diagram.edges]
    lines.append("@enduml")
    return fence("plantuml", lines)


def _element(node: Node) -> str:
    args = f'{node.alias}, "{_escape(node.label)}"'
    if node.description:
        args += f', "{_escape(node.description)}"'
    return f"{_C4_KEYWORDS[node.kind]}({args})"


def _escape(text: str) -> str:
    """Quoted string: whitespace collapsed, ``"`` as ``<U+0022>``."""
    return one_line(text).replace('"', "<U+0022>")
