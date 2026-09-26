"""Tests for the optional functional design doc (``extra_designs.functional_design``)."""

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.config import FeatureDocConfig, parse_config
from kingmadoc.exceptions import ConfigError

DESCRIPTION = "Add password reset via email. Links expire after 30 minutes."
FEATURES = Path("docs") / "features"
PLAN = FEATURES / "add-password-reset-via-email-plan.md"
FUNCTIONAL = FEATURES / "add-password-reset-via-email-functional-design.md"
TECHNICAL = FEATURES / "add-password-reset-via-email-technical-design.md"

SECTIONS = (
    "## User flows",
    "## Edge cases",
    "## Business rules",
    "## Permissions and roles",
)


def _config(root: Path, functional: bool, technical: bool = False) -> None:
    (root / ".featuredoc.yml").write_text(
        "extra_designs:\n"
        f"  functional_design:\n    enabled: {str(functional).lower()}\n"
        f"  technical_design:\n    enabled: {str(technical).lower()}\n",
        encoding="utf-8",
    )


def _plan(root: Path, *extra: str) -> Result:
    return CliRunner().invoke(cli, ["plan", DESCRIPTION, "--root", str(root), "--no-input", *extra])


def test_disabled_by_default(tmp_path: Path) -> None:
    """Without config, no functional design doc is written."""
    assert FeatureDocConfig().extra_designs.functional_design.enabled is False

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert not (tmp_path / FUNCTIONAL).exists()


def test_disabled_explicitly(tmp_path: Path) -> None:
    """``enabled: false`` behaves like the default."""
    _config(tmp_path, functional=False)

    assert _plan(tmp_path).exit_code == 0
    assert not (tmp_path / FUNCTIONAL).exists()


def test_enabled_writes_functional_design(tmp_path: Path) -> None:
    """When enabled, the doc is written next to the plan with all sections and a flowchart."""
    _config(tmp_path, functional=True)

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        str((tmp_path / PLAN).resolve()),
        str((tmp_path / FUNCTIONAL).resolve()),
    ]
    assert not (tmp_path / TECHNICAL).exists()
    doc = (tmp_path / FUNCTIONAL).read_text(encoding="utf-8")
    assert doc.startswith("# Functional design: Add password reset via email.\n")
    assert "[`add-password-reset-via-email-plan.md`](add-password-reset-via-email-plan.md)" in doc
    positions = [doc.find(section) for section in SECTIONS]
    assert -1 not in positions, [s for s, p in zip(SECTIONS, positions) if p == -1]
    assert positions == sorted(positions)
    flows = doc[positions[0]:positions[1]]
    assert "```mermaid\nflowchart TD\n" in flows


def test_both_extra_designs(tmp_path: Path) -> None:
    """Functional (what) is written and printed before technical (how)."""
    _config(tmp_path, functional=True, technical=True)

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        str((tmp_path / path).resolve()) for path in (PLAN, FUNCTIONAL, TECHNICAL)
    ]
    printed = _plan(tmp_path, "--stdout")
    assert printed.exit_code == 0, printed.output
    stdout = printed.stdout
    assert (
        stdout.index("# Feature:")
        < stdout.index("# Functional design:")
        < stdout.index("# Technical design:")
    )


@pytest.mark.parametrize(
    "data",
    [
        {"extra_designs": {"functional_design": {"enabled": 1}}},
        {"extra_designs": {"functional_design": {"enabled": True, "templates": "x"}}},
        {"extra_designs": {"functional": {"enabled": True}}},
        {"extra_designs": {"functional_design": True}},
    ],
)
def test_invalid_config_raises(data: dict) -> None:
    """Typos and wrong types are rejected like every other config key."""
    with pytest.raises(ConfigError):
        parse_config(data)


def test_empty_entry_means_disabled() -> None:
    """``functional_design:`` with no value parses as disabled, not as an error."""
    config = parse_config({"extra_designs": {"functional_design": None}})

    assert config.extra_designs.functional_design.enabled is False
