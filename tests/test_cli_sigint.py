"""Tests for Ctrl-C while `plan` asks its questions."""

from pathlib import Path
from types import SimpleNamespace

import click
import pytest
from click.testing import CliRunner

from kingmadoc import cli as cli_module
from kingmadoc.cli import _ask, cli


def _ctrl_c(*_args: object, **_kwargs: object) -> str:
    raise click.Abort()


def test_ctrl_c_in_a_terminal_aborts_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """In a real terminal, Ctrl-C aborts `plan` cleanly: exit 1, 'Aborted!', nothing written."""
    # CliRunner replaces sys.stdin during invoke, so fake the `sys` the CLI module sees.
    fake_sys = SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(cli_module, "sys", fake_sys)
    monkeypatch.setattr(cli_module.click, "prompt", _ctrl_c)

    result = CliRunner().invoke(cli, ["plan", "Add login.", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Aborted!" in result.output
    assert not (tmp_path / "docs").exists()


def test_ask_reraises_abort_in_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """_ask re-raises click.Abort when stdin is a terminal."""
    monkeypatch.setattr(cli_module.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(cli_module.click, "prompt", _ctrl_c)

    with pytest.raises(click.Abort):
        _ask(["Who?", "Why?"])


def test_ask_treats_abort_without_terminal_as_end_of_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a terminal (closed stdin), remaining questions are left unanswered."""
    monkeypatch.setattr(cli_module.sys.stdin, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(cli_module.click, "prompt", _ctrl_c)

    assert _ask(["Who?", "Why?"]) == [("Who?", ""), ("Why?", "")]
