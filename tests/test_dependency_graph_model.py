"""Tests for the dependency graph model in technical_design (roadmap WP9a)."""

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.plan import analyzer
from kingmadoc.plan.dependencies import collapse

TECHNICAL = Path("docs") / "features" / "add-x-technical-design.md"


def _project(root: Path, config: str) -> None:
    files = {
        "src/shop/__init__.py": "",
        "src/shop/cli.py": "from shop import orders\n",
        "src/shop/orders.py": "from shop.db import session\n",
        "src/shop/db.py": "",
    }
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    (root / ".featuredoc.yml").write_text(config, encoding="utf-8")


def _plan(root: Path) -> Result:
    return CliRunner().invoke(cli, ["plan", "Add x.", "--root", str(root), "--no-input"])


@pytest.mark.parametrize(
    ("fmt", "edge"),
    [
        ("mermaid", "shop_cli ..> shop_orders"),
        ("plantuml", "shop_cli ..> shop_orders"),
        ("d2", "shop_cli -> shop_orders"),
    ],
)
def test_technical_design_contains_the_graph(tmp_path: Path, fmt: str, edge: str) -> None:
    """The graph section shows the internal imports in the configured diagram format."""
    config = f"diagram_format: {fmt}\nextra_designs:\n  technical_design: {{enabled: true}}\n"
    _project(tmp_path, config)

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    doc = (tmp_path / TECHNICAL).read_text(encoding="utf-8")
    section = doc[doc.index("## Dependency graph"):]
    assert f"```{fmt}\n" in section
    assert edge in section
    assert "_(inferred)_" in section


def test_graph_is_not_computed_when_the_model_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Parsing every file is skipped unless the dependency graph model is selected."""
    _project(tmp_path, "extra_designs:\n  technical_design: {enabled: true, models: []}\n")

    def fail(*_args: object) -> tuple[()]:
        raise AssertionError("dependency graph computed although not selected")

    monkeypatch.setattr(analyzer, "_python_dependencies", fail)

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert "## Dependency graph" not in (tmp_path / TECHNICAL).read_text(encoding="utf-8")


def test_no_internal_imports_says_so(tmp_path: Path) -> None:
    """Without internal Python imports, the section explains instead of drawing nothing."""
    (tmp_path / ".featuredoc.yml").write_text(
        "extra_designs:\n  technical_design: {enabled: true}\n", encoding="utf-8"
    )
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.js").write_text("", encoding="utf-8")

    assert _plan(tmp_path).exit_code == 0

    doc = (tmp_path / TECHNICAL).read_text(encoding="utf-8")
    assert "No imports between the project's own Python modules" in doc


def test_collapse_keeps_small_graphs() -> None:
    """Graphs within the limit are unchanged."""
    edges = (("a.x", "a.y"), ("a.y", "b"))

    assert collapse(edges, max_nodes=25) == (edges, None)


def test_collapse_merges_to_package_level() -> None:
    """Too many modules are merged into their packages until the graph fits."""
    edges = tuple((f"app.api.m{i}", f"app.core.m{i}") for i in range(20))

    collapsed, depth = collapse(edges, max_nodes=25)

    assert depth == 2
    assert collapsed == (("app.api", "app.core"),)


def test_docstring_examples() -> None:
    """The examples in kingmadoc.plan.dependencies are real output."""
    import doctest

    from kingmadoc.plan import dependencies

    result = doctest.testmod(dependencies)

    assert result.attempted == 2
    assert result.failed == 0
