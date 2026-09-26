"""Tests for the Python module dependency graph (roadmap WP9a)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.config import AnalyzerConfig
from kingmadoc.plan.analyzer import analyze
from kingmadoc.plan.dependencies import module_dependencies, module_name


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/shop/orders.py", "shop.orders"),
        ("src/shop/__init__.py", "shop"),
        ("src/shop/api/routes.py", "shop.api.routes"),
        ("app/main.py", "app.main"),
        ("app/__init__.py", "app"),
    ],
)
def test_module_name(path: str, expected: str) -> None:
    """File paths map to dotted module names; `src/` is not part of the name."""
    assert module_name(Path(path)) == expected


FILES = {
    "src/shop/__init__.py": "__version__ = '1'\n",
    "src/shop/cli.py": "import shop.orders\nfrom shop import __version__\nimport click\n",
    "src/shop/orders.py": "from shop.db import session as s\nimport os, json\n",
    "src/shop/db.py": "import sqlalchemy\n",
    "src/shop/api/__init__.py": "",
    "src/shop/api/routes.py": "from ..orders import place\nfrom . import schemas\n",
    "src/shop/api/schemas.py": "from shop.api import routes  # cycle is fine\n",
    "src/shop/broken.py": "def (:\n",
}


def test_edges_from_absolute_relative_and_from_imports() -> None:
    """Internal imports become edges; stdlib and third-party imports are ignored."""
    edges = module_dependencies({Path(p): text for p, text in FILES.items()})

    assert set(edges) == {
        ("shop.cli", "shop.orders"),
        ("shop.cli", "shop"),
        ("shop.orders", "shop.db"),
        ("shop.api.routes", "shop.orders"),
        ("shop.api.routes", "shop.api.schemas"),
        ("shop.api.schemas", "shop.api.routes"),
    }
    assert list(edges) == sorted(edges)


def test_self_imports_and_unknown_relative_levels_are_ignored() -> None:
    """A module importing itself, or a relative import beyond the top, adds no edge."""
    files = {
        Path("app/a.py"): "import app.a\nfrom ....x import y\n",
        Path("app/b.py"): "",
    }

    assert module_dependencies(files) == ()


def test_analyzer_reports_dependencies_of_source_modules_only(tmp_path: Path) -> None:
    """The analyzer scans the source directories, not tests."""
    for path, text in {**FILES, "tests/test_cli.py": "import shop.cli\n"}.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")

    report = analyze(tmp_path, AnalyzerConfig(), with_dependencies=True)

    assert report.module_dependencies is not None
    assert ("shop.cli", "shop.orders") in report.module_dependencies
    assert not any("test" in a or "test" in b for a, b in report.module_dependencies)


def test_analyze_json_includes_dependencies(tmp_path: Path) -> None:
    """`kingmadoc analyze --json` exposes the edges as [source, target] pairs."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "a.py").write_text("from app import b\n", encoding="utf-8")
    (tmp_path / "app" / "b.py").write_text("", encoding="utf-8")

    result = CliRunner().invoke(cli, ["analyze", "--json", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["module_dependencies"] == [["app.a", "app.b"]]


def test_dependencies_are_only_computed_when_asked(tmp_path: Path) -> None:
    """Parsing every file is expensive, so a plain analysis leaves the graph as None."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "a.py").write_text("from app import b\n", encoding="utf-8")
    (tmp_path / "app" / "b.py").write_text("", encoding="utf-8")

    assert analyze(tmp_path, AnalyzerConfig()).module_dependencies is None
    assert analyze(tmp_path, AnalyzerConfig(), with_dependencies=True).module_dependencies == (
        ("app.a", "app.b"),
    )
