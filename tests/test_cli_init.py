"""Tests for `kingmadoc init`."""

from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.config import FeatureDocConfig, default_config_yaml, load_config


def test_init_writes_default_config(tmp_path: Path) -> None:
    """`init` writes the default config, which loads back as the defaults."""
    result = CliRunner().invoke(cli, ["init", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    target = tmp_path / ".featuredoc.yml"
    assert f"Created {target}" in result.output
    assert target.read_text(encoding="utf-8") == default_config_yaml()
    assert load_config(tmp_path) == FeatureDocConfig()


def test_init_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    """An existing config is kept unless --force is given."""
    target = tmp_path / ".featuredoc.yml"
    target.write_text("max_questions: 2\n", encoding="utf-8")

    refused = CliRunner().invoke(cli, ["init", "--root", str(tmp_path)])

    assert refused.exit_code == 1
    assert "already exists" in refused.output
    assert target.read_text(encoding="utf-8") == "max_questions: 2\n"


def test_init_force_overwrites(tmp_path: Path) -> None:
    """--force replaces an existing config with the defaults."""
    target = tmp_path / ".featuredoc.yml"
    target.write_text("max_questions: 2\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["init", "--root", str(tmp_path), "--force"])

    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") == default_config_yaml()
