"""Tests for opening explainers as a rendered preview in VS Code."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.vscode import EDITOR_ID, PREVIEW_PATTERN, enable_markdown_preview

SETTING = "workbench.editorAssociations"


def _settings(root: Path) -> Path:
    return root / ".vscode" / "settings.json"


def test_creates_settings_when_missing(tmp_path: Path) -> None:
    """A project without VS Code settings gets exactly the one association."""
    status = enable_markdown_preview(tmp_path)

    assert status.startswith("VS Code now opens")
    data = json.loads(_settings(tmp_path).read_text(encoding="utf-8"))
    assert data == {SETTING: {PREVIEW_PATTERN: EDITOR_ID}}


def test_keeps_existing_settings(tmp_path: Path) -> None:
    """Other settings and associations are kept."""
    _settings(tmp_path).parent.mkdir()
    _settings(tmp_path).write_text(
        json.dumps({"editor.tabSize": 2, SETTING: {"*.ipynb": "jupyter-notebook"}}),
        encoding="utf-8",
    )

    enable_markdown_preview(tmp_path)

    data = json.loads(_settings(tmp_path).read_text(encoding="utf-8"))
    assert data["editor.tabSize"] == 2
    assert data[SETTING] == {"*.ipynb": "jupyter-notebook", PREVIEW_PATTERN: EDITOR_ID}


def test_is_idempotent(tmp_path: Path) -> None:
    """Running again changes nothing."""
    enable_markdown_preview(tmp_path)
    before = _settings(tmp_path).read_text(encoding="utf-8")

    status = enable_markdown_preview(tmp_path)

    assert "already" in status
    assert _settings(tmp_path).read_text(encoding="utf-8") == before


def test_never_rewrites_settings_with_comments(tmp_path: Path) -> None:
    """VS Code settings may be JSONC; such a file is left alone, with instructions."""
    _settings(tmp_path).parent.mkdir()
    text = '{\n  // my settings\n  "editor.tabSize": 2,\n}\n'
    _settings(tmp_path).write_text(text, encoding="utf-8")

    status = enable_markdown_preview(tmp_path)

    assert PREVIEW_PATTERN in status and EDITOR_ID in status
    assert _settings(tmp_path).read_text(encoding="utf-8") == text


def test_does_not_override_a_different_choice(tmp_path: Path) -> None:
    """If the user associated the pattern with something else, that wins."""
    _settings(tmp_path).parent.mkdir()
    _settings(tmp_path).write_text(
        json.dumps({SETTING: {PREVIEW_PATTERN: "default"}}), encoding="utf-8"
    )

    status = enable_markdown_preview(tmp_path)

    assert "left unchanged" in status
    assert json.loads(_settings(tmp_path).read_text(encoding="utf-8")) == {
        SETTING: {PREVIEW_PATTERN: "default"}
    }


def test_skills_install_only_touches_vscode_when_asked(tmp_path: Path) -> None:
    """`skills install` leaves .vscode/ alone (with a tip); --vscode sets up the preview."""
    other = tmp_path / "other"
    other.mkdir()
    runner = CliRunner()

    plain = runner.invoke(cli, ["skills", "install", "--root", str(tmp_path)])
    asked = runner.invoke(cli, ["skills", "install", "--root", str(other), "--vscode"])

    assert plain.exit_code == 0, plain.output
    assert not _settings(tmp_path).exists()
    assert "--vscode" in plain.output
    assert asked.exit_code == 0, asked.output
    assert _settings(other).is_file()


def test_no_tip_when_the_preview_is_already_set_up(tmp_path: Path) -> None:
    """The --vscode tip is only shown while the setting is missing."""
    runner = CliRunner()
    first = runner.invoke(cli, ["skills", "install", "--root", str(tmp_path), "--vscode"])
    assert first.exit_code == 0, first.output

    again = runner.invoke(cli, ["skills", "install", "--root", str(tmp_path)])

    assert again.exit_code == 0, again.output
    assert "Tip" not in again.output


def test_an_interactive_install_asks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """In a terminal, skills install asks whether to set up the preview (default yes)."""
    from kingmadoc import cli as cli_module

    monkeypatch.setattr(cli_module, "_interactive", lambda: True)
    other = tmp_path / "other"
    other.mkdir()
    runner = CliRunner()

    yes = runner.invoke(cli, ["skills", "install", "--root", str(tmp_path)], input="\n")
    no = runner.invoke(cli, ["skills", "install", "--root", str(other)], input="n\n")

    assert yes.exit_code == 0, yes.output
    assert "rendered preview" in yes.output and _settings(tmp_path).is_file()
    assert no.exit_code == 0, no.output
    assert not _settings(other).exists()


def test_no_vscode_never_asks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--no-vscode: no question and no settings file, also in a terminal."""
    from kingmadoc import cli as cli_module

    monkeypatch.setattr(cli_module, "_interactive", lambda: True)

    result = CliRunner().invoke(
        cli, ["skills", "install", "--root", str(tmp_path), "--no-vscode"]
    )

    assert result.exit_code == 0, result.output
    assert "?" not in result.output
    assert not _settings(tmp_path).exists()
