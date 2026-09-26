"""Tests for Architecture Decision Records (``kingmadoc adr``)."""

import doctest
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc import adr as adr_module
from kingmadoc.adr import adr_filename, next_number, render_adr
from kingmadoc.cli import cli
from kingmadoc.exceptions import AdrError

ENABLED = "extra_designs:\n  adr:\n    enabled: true\n"
TODAY = date(2026, 9, 26)


def _adr(root: Path, title: str, *extra: str) -> Result:
    return CliRunner().invoke(cli, ["adr", title, "--root", str(root), *extra])


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project with ADRs enabled."""
    (tmp_path / ".featuredoc.yml").write_text(ENABLED, encoding="utf-8")
    return tmp_path


def test_first_adr_is_0001(project: Path) -> None:
    """With no docs/adr directory yet, the first ADR is 0001 and the directory is created."""
    result = _adr(project, "Use PostgreSQL for user data")

    assert result.exit_code == 0, result.output
    path = project / "docs" / "adr" / "0001-use-postgresql-for-user-data.md"
    assert result.stdout.strip() == str(path)
    assert path.read_text(encoding="utf-8").startswith("# 0001. Use PostgreSQL for user data\n")


def test_second_adr_is_0002(project: Path) -> None:
    """Each new ADR gets the next number."""
    assert _adr(project, "Use PostgreSQL").exit_code == 0

    result = _adr(project, "Drop Redis")

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (project / "docs" / "adr").iterdir()) == [
        "0001-use-postgresql.md",
        "0002-drop-redis.md",
    ]


def test_numbers_are_never_reused() -> None:
    """The next number follows the highest one, skipping gaps and non-ADR files."""
    assert next_number([]) == 1
    assert next_number(["README.md", "template.md", "notes.txt"]) == 1
    assert next_number(["0001-a.md", "0005-b.md", "0003-c.md"]) == 6
    assert next_number(["0009-a.md"]) == 10
    assert next_number(["9999-a.md"]) == 10000


@pytest.mark.parametrize(
    ("number", "title", "expected"),
    [
        (1, "Use PostgreSQL", "0001-use-postgresql.md"),
        (12, "  Switch to gRPC / HTTP2!  ", "0012-switch-to-grpc-http2.md"),
        (
            3,
            "Use the event-sourcing pattern for all order and payment data",
            "0003-use-the-event-sourcing-pattern-for-all.md",
        ),
        (4, "???", "0004-feature.md"),
        (10000, "Big", "10000-big.md"),
    ],
)
def test_slug_generation(number: int, title: str, expected: str) -> None:
    """File names are <NNNN>-<kebab-case slug, max 40 chars>.md."""
    assert adr_filename(number, title) == expected


def test_template_rendering(tmp_path: Path) -> None:
    """The ADR has the standard sections, in order, with number, date and status."""
    doc = render_adr(tmp_path, 7, "  Use   PostgreSQL ", status="accepted", today=TODAY)

    assert doc.startswith("# 0007. Use PostgreSQL\n")
    assert "Date: 2026-09-26\n" in doc
    sections = ["## Status", "## Context", "## Decision", "## Consequences"]
    positions = [doc.index(s) for s in sections]
    assert positions == sorted(positions)
    status = doc[positions[0]:positions[1]]
    assert "\nAccepted\n" in status
    assert "proposed, accepted, rejected, superseded" in status


@pytest.mark.parametrize("status", ["proposed", "accepted", "rejected", "superseded"])
def test_every_status_renders(tmp_path: Path, status: str) -> None:
    """All four statuses are valid."""
    doc = render_adr(tmp_path, 1, "X", status=status, today=TODAY)

    assert f"\n{status.capitalize()}\n" in doc


def test_invalid_input_raises(tmp_path: Path) -> None:
    """Blank titles and unknown statuses are errors."""
    with pytest.raises(AdrError, match="empty"):
        render_adr(tmp_path, 1, "   ", today=TODAY)
    with pytest.raises(AdrError, match="deprecated"):
        render_adr(tmp_path, 1, "X", status="deprecated", today=TODAY)


def test_cli_status_option(project: Path) -> None:
    """--status sets the status; other values are rejected by the CLI."""
    assert _adr(project, "A", "--status", "rejected").exit_code == 0
    assert "\nRejected\n" in (project / "docs" / "adr" / "0001-a.md").read_text(encoding="utf-8")
    assert _adr(project, "B", "--status", "maybe").exit_code == 2


def test_disabled_by_default(tmp_path: Path) -> None:
    """Without extra_designs.adr.enabled, the command explains how to enable it."""
    result = _adr(tmp_path, "Use PostgreSQL")

    assert result.exit_code == 1
    assert "extra_designs" in result.output
    assert not (tmp_path / "docs").exists()


def test_docstring_examples() -> None:
    """The examples in the docstrings are real output."""
    result = doctest.testmod(adr_module)

    assert result.attempted == 2
    assert result.failed == 0
