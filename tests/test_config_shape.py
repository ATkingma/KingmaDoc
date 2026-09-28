"""Regression tests for the public config shape and CLI surface (fix 6)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.config import parse_config
from kingmadoc.exceptions import ConfigError


def _config(root: Path, text: str) -> None:
    (root / ".featuredoc.yml").write_text(text, encoding="utf-8")


def test_adr_is_a_top_level_block_and_does_not_affect_plan(tmp_path: Path) -> None:
    """`adr.enabled` toggles `kingmadoc adr`; `plan` output is the same either way."""
    runner = CliRunner()
    _config(tmp_path, "adr:\n  enabled: true\n")

    adr = runner.invoke(cli, ["adr", "Use PostgreSQL", "--root", str(tmp_path)])
    plan = runner.invoke(cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input"])

    assert adr.exit_code == 0, adr.output
    assert (tmp_path / "docs" / "adr" / "0001-use-postgresql.md").is_file()
    assert plan.exit_code == 0, plan.output
    assert sorted(p.name for p in (tmp_path / "docs" / "features").iterdir()) == [
        "add-login-plan.md"
    ]

    _config(tmp_path, "adr:\n  enabled: false\n")
    disabled = runner.invoke(cli, ["adr", "Drop Redis", "--root", str(tmp_path)])
    assert disabled.exit_code == 1
    assert "adr:" in disabled.output


def test_adr_under_extra_designs_is_rejected() -> None:
    """The old location is an unknown key, so a stale config fails loudly."""
    with pytest.raises(ConfigError, match="adr"):
        parse_config({"extra_designs": {"adr": {"enabled": True}}})


def test_per_document_templates(tmp_path: Path) -> None:
    """Each extra design and the ADR block accept their own `template:` path."""
    (tmp_path / "func.md.j2").write_text("FUNCTIONAL {{ feature_summary }}\n", encoding="utf-8")
    (tmp_path / "adr.md.j2").write_text("ADR {{ number }} {{ title }}\n", encoding="utf-8")
    _config(
        tmp_path,
        "extra_designs:\n"
        "  functional_design: {enabled: true, template: ./func.md.j2}\n"
        "adr: {enabled: true, template: ./adr.md.j2}\n",
    )
    runner = CliRunner()

    plan = runner.invoke(cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input"])
    adr = runner.invoke(cli, ["adr", "Use SQLite", "--root", str(tmp_path)])

    assert plan.exit_code == 0, plan.output
    features = tmp_path / "docs" / "features"
    assert (features / "add-login-functional-design.md").read_text(
        encoding="utf-8"
    ) == "FUNCTIONAL Add login.\n"
    assert adr.exit_code == 0, adr.output
    assert (tmp_path / "docs" / "adr" / "0001-use-sqlite.md").read_text(
        encoding="utf-8"
    ) == "ADR 0001 Use SQLite\n"


def test_analyze_prints_json_and_plan_requires_a_description(tmp_path: Path) -> None:
    """`analyze --json` is the analysis; `plan` always needs a description."""
    (tmp_path / "main.py").write_text("import click\n", encoding="utf-8")
    runner = CliRunner()

    analyzed = runner.invoke(cli, ["analyze", "--json", "--root", str(tmp_path)])
    no_description = runner.invoke(cli, ["plan", "--root", str(tmp_path)])
    old_flag = runner.invoke(cli, ["plan", "--json", "--root", str(tmp_path)])

    assert analyzed.exit_code == 0, analyzed.output
    data = json.loads(analyzed.stdout)
    assert data["entry_points"] == ["main.py"]
    assert "Click" in data["detected_stack"]
    assert no_description.exit_code == 2
    assert "Missing argument" in no_description.output
    assert old_flag.exit_code == 2
    assert not (tmp_path / "docs").exists()


def test_analyze_without_json_prints_a_summary(tmp_path: Path) -> None:
    """Without --json, analyze prints a short human-readable report."""
    (tmp_path / "main.py").write_text("", encoding="utf-8")

    result = CliRunner().invoke(cli, ["analyze", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Files: 1" in result.stdout
    assert "Entry points: main.py" in result.stdout


def test_the_repositorys_own_config_loads() -> None:
    """The repo's .featuredoc.yml stays valid when models or keys change (it once lagged)."""
    from pathlib import Path

    from kingmadoc.config import load_config

    root = Path(__file__).resolve().parents[1]
    load_config(root, None)
