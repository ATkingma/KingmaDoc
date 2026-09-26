"""End-to-end tests: run ``kingmadoc plan`` on a temporary project."""

from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli

SECTIONS = (
    "# Feature: Add password reset via email.",
    "## One-sentence summary",
    "## Scope (in / out)",
    "## Assumptions",
    "## Risks",
    "## C4 Context (Mermaid)",
    "## C4 Container (Mermaid)",
    "## Open questions",
)

DESCRIPTION = "Add password reset via email. Users get a link that expires after 30 minutes."


def _project(root: Path) -> None:
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text("from fastapi import FastAPI\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["fastapi", "psycopg2"]\n', encoding="utf-8"
    )


def test_plan_writes_doc_with_all_sections(tmp_path: Path) -> None:
    """Defaults (no config file): doc lands in docs/features/<slug>-plan.md."""
    _project(tmp_path)

    result = CliRunner().invoke(cli, ["plan", DESCRIPTION, "--root", str(tmp_path), "--no-input"])

    assert result.exit_code == 0, result.output
    path = tmp_path / "docs" / "features" / "add-password-reset-via-email-plan.md"
    assert result.stdout.strip() == str(path.resolve())
    doc = path.read_text(encoding="utf-8")
    positions = [doc.find(section) for section in SECTIONS]
    assert -1 not in positions, [s for s, p in zip(SECTIONS, positions) if p == -1]
    assert positions == sorted(positions), "sections are out of order"
    assert doc.count("```mermaid") == 2
    assert "FastAPI" in doc and "PostgreSQL" in doc
    assert "- [ ] What problem does this feature solve, and for whom?" in doc


def test_plan_respects_config(tmp_path: Path) -> None:
    """``.featuredoc.yml`` changes the output directory and the diagrams."""
    _project(tmp_path)
    (tmp_path / ".featuredoc.yml").write_text(
        "output_dir: plans\ndiagrams: [c4_context]\n", encoding="utf-8"
    )

    result = CliRunner().invoke(cli, ["plan", DESCRIPTION, "--root", str(tmp_path), "--no-input"])

    assert result.exit_code == 0, result.output
    doc = (tmp_path / "plans" / "add-password-reset-via-email-plan.md").read_text(encoding="utf-8")
    assert doc.count("```mermaid") == 1
    assert "## C4 Container (Mermaid)" in doc


def test_plan_refuses_to_overwrite(tmp_path: Path) -> None:
    """A second run fails unless --force is given."""
    args = ["plan", DESCRIPTION, "--root", str(tmp_path), "--no-input"]
    runner = CliRunner()

    assert runner.invoke(cli, args).exit_code == 0
    second = runner.invoke(cli, args)
    assert second.exit_code == 1
    assert "already exists" in second.output
    assert runner.invoke(cli, [*args, "--force"]).exit_code == 0


def test_plan_requires_description(tmp_path: Path) -> None:
    """Without --json, the description is mandatory and may not be blank."""
    runner = CliRunner()

    assert runner.invoke(cli, ["plan", "--root", str(tmp_path)]).exit_code == 2
    blank = runner.invoke(cli, ["plan", "  ", "--root", str(tmp_path), "--no-input"])
    assert blank.exit_code == 1
    assert "must not be empty" in blank.output
