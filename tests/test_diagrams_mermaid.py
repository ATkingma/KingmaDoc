"""Snapshot tests for the Mermaid backend (kingmadoc.diagrams.mermaid)."""

import doctest
from pathlib import Path

import pytest

from kingmadoc.diagrams import base, mermaid
from kingmadoc.diagrams.mermaid import render_component, render_container, render_context
from kingmadoc.exceptions import DiagramError

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8").rstrip("\n")


def test_render_context_snapshot() -> None:
    """Actors, external systems, quote escaping and default relationships."""
    output = render_context(
        'Web "Shop"',
        [{"name": "Customer", "description": 'Buys "things"\n online'}, {"name": "Admin"}],
        [{"name": "Stripe", "description": "Card payments"}, {"name": "PostgreSQL"}],
    )

    assert output == _fixture("context.mmd")


def test_render_container_snapshot() -> None:
    """Boundary, actors, explicit relationships, duplicate aliases and missing keys."""
    output = render_container(
        "Shop",
        [
            {"name": "Web", "tech": "React", "description": 'Storefront, a "SPA"'},
            {"name": "API", "tech": "FastAPI", "description": "Orders"},
            {"name": "api", "tech": "Python"},
            {"name": "DB"},
        ],
        relationships=[
            ("Customer", "Web", "Visits"),
            ("Web", "API", 'Calls "/orders"'),
            ("API", "DB", "Reads/writes"),
        ],
        external_actors=[{"name": "Customer", "description": "Buys things"}],
    )

    assert output == _fixture("container.mmd")


def test_render_component_snapshot() -> None:
    """Container boundary with components and relationships."""
    output = render_component(
        "API",
        [
            {"name": "OrderRouter", "tech": "FastAPI", "description": "HTTP routes"},
            {"name": "OrderService", "tech": "Python", "description": "Business rules"},
            {"name": "OrderRepo", "tech": "SQLAlchemy", "description": "Persistence"},
        ],
        relationships=[
            ("OrderRouter", "OrderService", "Delegates to"),
            ("OrderService", "OrderRepo", "Reads/writes"),
        ],
    )

    assert output == _fixture("component.mmd")


def test_render_context_explicit_relationships_replace_defaults() -> None:
    """default_relationships=False disables the default arrows."""
    output = render_context("Shop", [{"name": "Customer"}], [], default_relationships=False)

    assert "Rel(" not in output


def test_every_renderer_returns_fenced_block() -> None:
    """Output is always a complete ```mermaid block."""
    for output in (
        render_context("S", [], []),
        render_container("S", []),
        render_component("C", []),
    ):
        assert output.startswith("```mermaid\n")
        assert output.endswith("\n```")


def test_unknown_relationship_element_raises() -> None:
    """A relationship to an element that is not in the diagram is an error."""
    with pytest.raises(DiagramError, match="Nope"):
        render_component("API", [{"name": "Router"}], relationships=[("Router", "Nope", "x")])


def test_element_without_name_raises() -> None:
    """Every element needs a non-empty name."""
    with pytest.raises(DiagramError, match="without a name"):
        render_container("Shop", [{"tech": "Python"}])


def test_docstring_examples() -> None:
    """The examples in the docstrings are real output."""
    for module, examples in ((mermaid, 3), (base, 2)):
        result = doctest.testmod(module)

        assert result.attempted == examples, module.__name__
        assert result.failed == 0, module.__name__


def test_title_drops_characters_that_end_a_c4_title() -> None:
    """Mermaid's C4 lexer stops a title at ``#`` or ``;``; quotes stay literal."""
    output = render_component('C# "Core"; v2', [])

    assert '    title Components: C "Core", v2\n' in output


def test_container_may_share_the_system_name() -> None:
    """Relationships target the container, not the same-named system boundary."""
    output = render_container(
        "Shop", [{"name": "Shop"}], relationships=[("User", "Shop", "Uses")],
        external_actors=[{"name": "User"}],
    )

    assert "System_Boundary(shop_boundary, " in output
    assert "Container(shop, " in output
    assert "Rel(user, shop, " in output


def test_context_system_description() -> None:
    """The optional system description ends up on the system box."""
    output = render_context("Shop", [], [], system_description='Sells "stuff"')

    assert '    System(shop, "Shop", "Sells #quot;stuff#quot;")' in output
