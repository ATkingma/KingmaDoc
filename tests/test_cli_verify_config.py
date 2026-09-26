"""Tests for `kingmadoc verify --config`."""

from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli


def test_verify_uses_the_given_config_file(tmp_path: Path) -> None:
    """--config points verify at a config (and so an output_dir) outside the default name."""
    (tmp_path / "custom.yml").write_text("output_dir: plans\n", encoding="utf-8")
    plans = tmp_path / "plans"
    plans.mkdir()
    (plans / "add-login-plan.md").write_text("# Feature: Add login.\n", encoding="utf-8")
    runner = CliRunner()

    without = runner.invoke(cli, ["verify", "add-login", "--root", str(tmp_path)])
    with_config = runner.invoke(
        cli, ["verify", "add-login", "--root", str(tmp_path), "-c", str(tmp_path / "custom.yml")]
    )

    assert without.exit_code == 1  # default output_dir docs/features has no plan
    assert with_config.exit_code == 0, with_config.output
    assert (plans / "add-login-verify.md").is_file()


def test_verify_with_missing_config_file_fails(tmp_path: Path) -> None:
    """A --config path that does not exist is an error, not silently ignored."""
    result = CliRunner().invoke(
        cli, ["verify", "add-login", "--root", str(tmp_path), "-c", str(tmp_path / "nope.yml")]
    )

    assert result.exit_code == 1
    assert "Config file not found" in result.output
