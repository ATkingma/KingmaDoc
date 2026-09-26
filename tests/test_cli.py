"""Tests for kingmadoc.cli."""

from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli


def test_plan_without_stdin_skips_questions(tmp_path: Path) -> None:
    """Closed stdin (e.g. an AI agent) must not abort ``plan``."""
    (tmp_path / "app.py").write_text("import click\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["plan", "Login", "--root", str(tmp_path)], input="")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "docs" / "features" / "login-plan.md").is_file()


def test_plan_uses_piped_answers(tmp_path: Path) -> None:
    """Answers piped on stdin end up in the doc."""
    result = CliRunner().invoke(
        cli, ["plan", "Login", "--root", str(tmp_path), "--stdout"], input="Users need login\n"
    )

    assert result.exit_code == 0, result.output
    assert "Users need login" in result.output
