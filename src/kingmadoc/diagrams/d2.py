"""D2 backend. D2 has no C4 keywords, so C4 is drawn with plain D2 shapes: people are
``shape: person``, external systems are dashed, boundaries are containers (edges then
refer to nested elements by path, e.g. ``shop_boundary.web``). Sequence and class
diagrams use D2's ``sequence_diagram`` and ``class`` shapes.

Escaping: labels are double-quoted strings with ``\\``, ``"`` and ``$`` (variable
substitution) backslash-escaped; multi-line labels use ``\\n``.

Example:
    >>> print(render_context("Shop", [{"name": "Customer"}], []))
    ```d2
    title: "System Context: Shop" {
      shape: text
      near: top-center
      style.font-size: 24
    }
    customer: "Customer" {
      shape: person
    }
    shop: "Shop"
    customer -> shop: "Uses"
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
    split_member,
)

LABEL = "D2"

# D2 keywords that cannot be used as object ids (aliases are [a-z0-9_]).
_RESERVED_IDS = frozenset({
    "shape", "label", "style", "icon", "near", "width", "height", "direction", "tooltip",
    "link", "constraint", "title", "vars", "classes", "class", "top", "left", "layers",
    "scenarios", "steps", "null", "grid_rows", "grid_columns", "filled",
})
# Class relationship kind -> edge attribute lines.
_CLASS_EDGE_STYLES = MappingProxyType({
    "inherits": ("target-arrowhead.shape: triangle", "target-arrowhead.style.filled: false"),
    "composition": ("source-arrowhead.shape: diamond", "source-arrowhead.style.filled: true"),
    "aggregation": ("source-arrowhead.shape: diamond", "source-arrowhead.style.filled: false"),
    "association": (),
    "dependency": ("style.stroke-dash: 3",),
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
    """Render a C4 Context diagram in D2; see :func:`kingmadoc.diagrams.base.build_context`.

    Args:
        system_name: The system being documented.
        external_actors: People who use the system.
        external_systems: Systems it depends on.
        relationships: ``(source, target, label)``, drawn after the defaults.
        system_description: Optional description on the system box.
        default_relationships: Also draw actor -> system and system -> external arrows.

    Returns:
        A fenced ``d2`` block.
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
    """Render a C4 Container diagram in D2 (containers nested in the system boundary).

    Args:
        system_name: The system whose boundary holds the containers.
        containers: ``name``, ``tech``, ``description``.
        relationships: ``(source, target, label)`` by name.
        external_actors: People drawn outside the boundary.

    Returns:
        A fenced ``d2`` block.
    """
    return _c4(build_container(system_name, containers, relationships, external_actors))


def render_component(
    container_name: str,
    components: Sequence[Element],
    relationships: Sequence[Rel] = (),
) -> str:
    """Render a C4 Component diagram in D2 (components nested in the container).

    Args:
        container_name: The container whose boundary holds the components.
        components: ``name``, ``tech``, ``description``.
        relationships: ``(source, target, label)`` by name.

    Returns:
        A fenced ``d2`` block.
    """
    return _c4(build_component(container_name, components, relationships))


def render_sequence(
    title: str, participants: Sequence[Element], messages: Sequence[Rel]
) -> str:
    """Render a D2 ``sequence_diagram``, labelled with the title.

    Args:
        title: Diagram title.
        participants: Drawn left to right in this order.
        messages: ``(sender, receiver, text)`` in time order.

    Returns:
        A fenced ``d2`` block.
    """
    diagram = build_sequence(title, participants, messages)
    lines = [f"diagram: {_q(diagram.title)} {{", "  shape: sequence_diagram"]
    lines += [f"  {_id(n.alias)}: {_q(n.label)}" for n in diagram.nodes]
    lines += [f"  {_id(e.source)} -> {_id(e.target)}: {_q(e.label)}" for e in diagram.edges]
    lines.append("}")
    return fence("d2", lines)


def render_class(
    title: str, classes: Sequence[ClassSpec], relationships: Sequence[ClassRel] = ()
) -> str:
    """Render a D2 class diagram (``shape: class`` objects).

    Args:
        title: Diagram title.
        classes: ``name``, ``attributes``, ``methods``.
        relationships: ``(source, target, kind, label)`` by class name.

    Returns:
        A fenced ``d2`` block.
    """
    diagram = build_class(title, classes, relationships)
    lines = _title(diagram.title)
    for node in diagram.nodes:
        lines.append(f"{_id(node.alias)}: {_q(node.label)} {{")
        lines.append("  shape: class")
        for member in (*node.attributes, *node.methods):
            signature, typ = split_member(member)
            lines.append(f"  {_q(signature)}: {_q(typ)}" if typ else f"  {_q(signature)}")
        lines.append("}")
    for edge in diagram.edges:
        head = f"{_id(edge.source)} -> {_id(edge.target)}"
        if edge.label:
            head += f": {_q(edge.label)}"
        styles = _CLASS_EDGE_STYLES[edge.kind]
        if not styles:
            lines.append(head)
            continue
        lines.append(head + " {")
        lines += [f"  {style}" for style in styles]
        lines.append("}")
    return fence("d2", lines)


def _c4(diagram: Diagram) -> str:
    lines = _title(diagram.title)
    lines += _node(diagram.nodes, indent="")
    if diagram.boundary is not None:
        b = diagram.boundary
        lines.append(f"{_id(b.alias)}: {_q(b.label)} {{")
        lines += _node(diagram.children, indent="  ")
        lines.append("}")
    lines += [
        f"{_path(diagram, e.source)} -> {_path(diagram, e.target)}: {_q(e.label)}"
        for e in diagram.edges
    ]
    return fence("d2", lines)


def _node(nodes: Sequence[Node], indent: str) -> list[str]:
    lines = []
    for node in nodes:
        parts = [node.label]
        if node.technology:
            parts.append(f"[{node.technology}]")
        if node.description:
            parts.append(node.description)
        head = f"{indent}{_id(node.alias)}: {_q(*parts)}"
        if node.kind == "person":
            lines += [head + " {", f"{indent}  shape: person", f"{indent}}}"]
        elif node.kind == "system_ext":
            lines += [head + " {", f"{indent}  style.stroke-dash: 3", f"{indent}}}"]
        else:
            lines.append(head)
    return lines


def _title(title: str) -> list[str]:
    return [
        f"title: {_q(title)} {{",
        "  shape: text",
        "  near: top-center",
        "  style.font-size: 24",
        "}",
    ]


def _path(diagram: Diagram, alias: str) -> str:
    parent = diagram.parent_of(alias)
    return f"{_id(parent.alias)}.{_id(alias)}" if parent else _id(alias)


def _id(alias: str) -> str:
    return f"{alias}_" if alias in _RESERVED_IDS else alias


def _q(*lines: str) -> str:
    """Double-quoted D2 string; each argument becomes one line of the label."""
    escaped = (
        one_line(line).replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
        for line in lines
    )
    return '"' + "\\n".join(escaped) + '"'
