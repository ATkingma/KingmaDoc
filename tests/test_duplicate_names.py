"""Regression tests: elements with the same name must not produce wrong arrows."""

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.diagrams import BACKENDS
from kingmadoc.exceptions import DiagramError


def _plan(root: Path) -> str:
    result = CliRunner().invoke(
        cli, ["plan", "Add x.", "--root", str(root), "--no-input", "--stdout"]
    )
    assert result.exit_code == 0, result.output
    return result.stdout


def _rels(doc: str) -> list[tuple[str, str]]:
    return re.findall(r"Rel\((\w+), (\w+),", doc)


def test_project_named_like_the_actor(tmp_path: Path) -> None:
    """The reported case: `project.name: User` gave Rel(user, user) and an orphan actor."""
    (tmp_path / ".featuredoc.yml").write_text("project: {name: User}\n", encoding="utf-8")

    doc = _plan(tmp_path)

    rels = _rels(doc)
    assert rels and all(source != target for source, target in rels)
    actor = re.search(r"Person\((\w+),", doc).group(1)
    assert any(source == actor for source, _ in rels)


def test_same_directory_name_in_two_places(tmp_path: Path) -> None:
    """`app/` and `src/app/` become two containers with distinct names."""
    for name in ("app/a.py", "src/app/b.py"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("", encoding="utf-8")

    doc = _plan(tmp_path)

    labels = re.findall(r'Container\(\w+, "([^"]+)"', doc)
    assert sorted(labels) == ["app", "src/app"]


@pytest.mark.parametrize("fmt", BACKENDS)
def test_duplicate_names_are_rejected(fmt: str) -> None:
    """Relationships refer to names, so two elements may not share one."""
    backend = BACKENDS[fmt]

    with pytest.raises(DiagramError, match="Duplicate element name 'API'"):
        backend.render_container("Shop", [{"name": "API"}, {"name": "API"}])
    with pytest.raises(DiagramError, match="Duplicate element name 'Shop'"):
        backend.render_context("Shop", [{"name": "Shop"}], [])
