"""Tests for the optional technical design doc (``extra_designs.technical_design``)."""

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.config import FeatureDocConfig, parse_config
from kingmadoc.exceptions import ConfigError

DESCRIPTION = "Add password reset via email. Links expire after 30 minutes."
FEATURES = Path("docs") / "features"
PLAN = FEATURES / "add-password-reset-via-email-plan.md"
TECHNICAL = FEATURES / "add-password-reset-via-email-technical-design.md"

SECTIONS = (
    "## Database schema",
    "## API contracts",
    "## Error handling",
    "## Performance considerations",
    "## Security considerations",
)

ENABLED = "extra_designs:\n  technical_design:\n    enabled: true\n"


def _plan(root: Path, *extra: str) -> Result:
    return CliRunner().invoke(cli, ["plan", DESCRIPTION, "--root", str(root), "--no-input", *extra])


def test_disabled_by_default(tmp_path: Path) -> None:
    """Without config, only the plan doc is written and printed."""
    assert FeatureDocConfig().extra_designs.technical_design.enabled is False

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert (tmp_path / PLAN).is_file()
    assert not (tmp_path / TECHNICAL).exists()
    assert result.stdout.splitlines() == [str((tmp_path / PLAN).resolve())]


def test_disabled_explicitly(tmp_path: Path) -> None:
    """``enabled: false`` behaves like the default."""
    (tmp_path / ".featuredoc.yml").write_text(ENABLED.replace("true", "false"), encoding="utf-8")

    assert _plan(tmp_path).exit_code == 0
    assert not (tmp_path / TECHNICAL).exists()


def test_enabled_writes_technical_design(tmp_path: Path) -> None:
    """When enabled, the technical design doc is written next to the plan with all sections."""
    (tmp_path / ".featuredoc.yml").write_text(ENABLED, encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("fastapi\npsycopg2\n", encoding="utf-8")

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        str((tmp_path / PLAN).resolve()),
        str((tmp_path / TECHNICAL).resolve()),
    ]
    doc = (tmp_path / TECHNICAL).read_text(encoding="utf-8")
    assert doc.startswith("# Technical design: Add password reset via email.\n")
    assert "[`add-password-reset-via-email-plan.md`](add-password-reset-via-email-plan.md)" in doc
    positions = [doc.find(section) for section in SECTIONS]
    assert -1 not in positions, [s for s, p in zip(SECTIONS, positions) if p == -1]
    assert positions == sorted(positions)
    schema = doc[positions[0]:positions[1]]
    assert "```mermaid\nerDiagram\n" in schema
    assert "Data stores detected in the codebase: PostgreSQL." in schema


def test_enabled_without_database(tmp_path: Path) -> None:
    """No detected database is stated, not guessed."""
    (tmp_path / ".featuredoc.yml").write_text(ENABLED, encoding="utf-8")

    assert _plan(tmp_path).exit_code == 0
    assert "No database detected" in (tmp_path / TECHNICAL).read_text(encoding="utf-8")


def test_enabled_with_custom_output(tmp_path: Path) -> None:
    """With --output, the technical design doc goes next to the custom plan path."""
    (tmp_path / ".featuredoc.yml").write_text(ENABLED, encoding="utf-8")
    out = tmp_path / "plans" / "reset.md"

    assert _plan(tmp_path, "-o", str(out)).exit_code == 0
    assert (tmp_path / "plans" / "reset-technical-design.md").is_file()


def test_enabled_stdout_prints_both(tmp_path: Path) -> None:
    """--stdout prints the plan, a horizontal rule, then the technical design."""
    (tmp_path / ".featuredoc.yml").write_text(ENABLED, encoding="utf-8")

    result = _plan(tmp_path, "--stdout")

    assert result.exit_code == 0, result.output
    assert result.stdout.index("# Feature:") < result.stdout.index("\n---\n\n# Technical design:")
    assert not (tmp_path / "docs").exists()


def test_existing_technical_design_blocks_both_writes(tmp_path: Path) -> None:
    """If either target exists, nothing is written (unless --force)."""
    (tmp_path / ".featuredoc.yml").write_text(ENABLED, encoding="utf-8")
    (tmp_path / FEATURES).mkdir(parents=True)
    (tmp_path / TECHNICAL).write_text("keep me", encoding="utf-8")

    result = _plan(tmp_path)

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert not (tmp_path / PLAN).exists()
    assert (tmp_path / TECHNICAL).read_text(encoding="utf-8") == "keep me"
    assert _plan(tmp_path, "--force").exit_code == 0


@pytest.mark.parametrize(
    "data",
    [
        {"extra_designs": {"technical_design": {"enabled": "yes"}}},
        {"extra_designs": {"technical_design": {"enable": True}}},
        {"extra_designs": {"api_design": {"enabled": True}}},
        {"extra_designs": ["technical_design"]},
    ],
)
def test_invalid_config_raises(data: dict) -> None:
    """Typos and wrong types are rejected like every other config key."""
    with pytest.raises(ConfigError):
        parse_config(data)
