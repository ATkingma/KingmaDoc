"""Mermaid backend: ``C4Context``/``C4Container``/``C4Component``, ``sequenceDiagram``,
``classDiagram``. The default ``diagram_format``.

Escaping: ``"`` in quoted labels becomes the Mermaid entity ``#quot;`` (rendered as a
quote). C4 titles end at ``#`` or ``;``, so those are dropped from titles.

Example:
    >>> print(render_context(
    ...     "Shop",
    ...     [{"name": "Customer", "description": "Buys things"}],
    ...     [{"name": "Stripe", "description": 'Card "payments"'}],
    ... ))
    ```mermaid
    C4Context
        title System Context: Shop
    <BLANKLINE>
        Person(customer, "Customer", "Buys things")
        System(shop, "Shop")
        System_Ext(stripe, "Stripe", "Card #quot;payments#quot;")
    <BLANKLINE>
        Rel(customer, shop, "Uses")
        Rel(shop, stripe, "Uses")
    ```
"""

from __future__ import annotations

import re
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

LABEL = "Mermaid"

_ENTITIES = MappingProxyType({"#": "#35;", ";": "#59;", '"': "#quot;"})

_C4_KEYWORDS = MappingProxyType({
    "person": "Person",
    "system": "System",
    "system_ext": "System_Ext",
    "container": "Container",
    "component": "Component",
})
_C4_HEADERS = MappingProxyType(
    {"context": "C4Context", "container": "C4Container", "component": "C4Component"}
)
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
    """Render a Mermaid ``C4Context`` diagram; see :func:`kingmadoc.diagrams.base.build_context`.

    Args:
        system_name: The system being documented.
        external_actors: People who use the system.
        external_systems: Systems it depends on.
        relationships: ``(source, target, label)``, drawn after the defaults.
        system_description: Optional description on the system box.
        default_relationships: Also draw actor -> system and system -> external arrows.

    Returns:
        A fenced ``mermaid`` block.
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
    """Render a Mermaid ``C4Container`` diagram.

    Args:
        system_name: The system whose boundary holds the containers.
        containers: ``name``, ``tech``, ``description``.
        relationships: ``(source, target, label)`` by name.
        external_actors: People drawn outside the boundary.

    Returns:
        A fenced ``mermaid`` block.

    Example:
        >>> print(render_container(
        ...     "Shop",
        ...     [{"name": "Web", "tech": "React", "description": "Storefront"},
        ...      {"name": "API", "tech": "FastAPI", "description": "Orders"}],
        ...     relationships=[("Web", "API", "Calls")],
        ... ))
        ```mermaid
        C4Container
            title Containers: Shop
        <BLANKLINE>
            System_Boundary(shop_boundary, "Shop") {
                Container(web, "Web", "React", "Storefront")
                Container(api, "API", "FastAPI", "Orders")
            }
        <BLANKLINE>
            Rel(web, api, "Calls")
        ```
    """
    return _c4(build_container(system_name, containers, relationships, external_actors))


def render_component(
    container_name: str,
    components: Sequence[Element],
    relationships: Sequence[Rel] = (),
) -> str:
    """Render a Mermaid ``C4Component`` diagram.

    Args:
        container_name: The container whose boundary holds the components.
        components: ``name``, ``tech``, ``description``.
        relationships: ``(source, target, label)`` by name.

    Returns:
        A fenced ``mermaid`` block.
    """
    return _c4(build_component(container_name, components, relationships))


def render_sequence(
    title: str, participants: Sequence[Element], messages: Sequence[Rel]
) -> str:
    """Render a Mermaid ``sequenceDiagram``.

    Args:
        title: Diagram title.
        participants: Drawn left to right in this order.
        messages: ``(sender, receiver, text)`` in time order.

    Returns:
        A fenced ``mermaid`` block.

    Example:
        >>> print(render_sequence(
        ...     "Login",
        ...     [{"name": "Web App"}, {"name": "API"}],
        ...     [("Web App", "API", "POST /login"), ("API", "Web App", "200 OK")],
        ... ))
        ```mermaid
        sequenceDiagram
            title Login
            participant web_app as Web App
            participant api as API
            web_app->>api: POST /login
            api->>web_app: 200 OK
        ```
    """
    diagram = build_sequence(title, participants, messages)
    lines = ["sequenceDiagram", f"    title {_text(diagram.title)}"]
    lines += [f"    participant {n.alias} as {_text(n.label)}" for n in diagram.nodes]
    lines += [f"    {e.source}->>{e.target}: {_text(e.label)}" for e in diagram.edges]
    return fence("mermaid", lines)


def render_class(
    title: str, classes: Sequence[ClassSpec], relationships: Sequence[ClassRel] = ()
) -> str:
    """Render a Mermaid ``classDiagram`` (title in YAML frontmatter, as Mermaid requires).

    Args:
        title: Diagram title.
        classes: ``name``, ``attributes``, ``methods``.
        relationships: ``(source, target, kind, label)`` by class name.

    Returns:
        A fenced ``mermaid`` block.
    """
    diagram = build_class(title, classes, relationships)
    title_yaml = one_line(diagram.title).replace("\\", "\\\\").replace('"', '\\"')
    lines = ["---", f'title: "{title_yaml}"', "---", "classDiagram"]
    for node in diagram.nodes:
        header = f'    class {node.alias}["{_escape(node.label)}"]'
        members = [*node.attributes, *(_method(m) for m in node.methods)]
        if not members:
            lines.append(header)
            continue
        lines.append(header + " {")
        lines += [f"        {_member(m)}" for m in members]
        lines.append("    }")
    for edge in diagram.edges:
        arrow, swap = _CLASS_ARROWS[edge.kind]
        left, right = (edge.target, edge.source) if swap else (edge.source, edge.target)
        label = f" : {_text(edge.label)}" if edge.label else ""
        lines.append(f"    {left} {arrow} {right}{label}")
    return fence("mermaid", lines)


def _c4(diagram: Diagram) -> str:
    lines = [_C4_HEADERS[diagram.kind], f"    title {_title(diagram.title)}", ""]
    lines += [_element(n) for n in diagram.nodes]
    if diagram.boundary is not None:
        b = diagram.boundary
        lines.append(f'    {_BOUNDARIES[diagram.kind]}({b.alias}, "{_escape(b.label)}") {{')
        lines += [
            f'        {_C4_KEYWORDS[c.kind]}({c.alias}, "{_escape(c.label)}", '
            f'"{_escape(c.technology)}", "{_escape(c.description)}")'
            for c in diagram.children
        ]
        lines.append("    }")
    if diagram.edges:
        lines.append("")
        lines += [
            f'    Rel({e.source}, {e.target}, "{_escape(e.label)}")' for e in diagram.edges
        ]
    return fence("mermaid", lines)


def _element(node: Node) -> str:
    args = f'{node.alias}, "{_escape(node.label)}"'
    if node.description:
        args += f', "{_escape(node.description)}"'
    return f"    {_C4_KEYWORDS[node.kind]}({args})"


def _method(member: str) -> str:
    # Mermaid writes a method's return type after a space: "login(pw) bool".
    signature, typ = split_member(member)
    return f"{signature} {typ}".strip()


def _member(member: str) -> str:
    # Braces would close the class body early.
    return member.replace("{", "(").replace("}", ")")


def _title(text: str) -> str:
    """C4 titles end at ``#`` or ``;``; quotes are fine because titles are unquoted."""
    return " ".join(text.replace("#", " ").replace(";", ",").split())


def _escape(text: str) -> str:
    """Quoted label: whitespace collapsed, ``"`` as the entity ``#quot;``."""
    return one_line(text).replace('"', "#quot;")


def _text(text: str) -> str:
    """Unquoted text (sequence labels, class relationship labels).

    ``;`` separates statements and ``#…;`` starts an entity, so ``#``, ``;`` and ``"``
    are all written as entities, in a single pass (so entities are not escaped twice).
    """
    return re.sub(r'[#;"]', lambda m: _ENTITIES[m.group()], one_line(text))
