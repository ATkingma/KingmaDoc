"""Regression tests: ``output_dir`` must stay inside the project root (fix 2)."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli


def _config(root: Path, output_dir: str) -> None:
    (root / ".featuredoc.yml").write_text(f"output_dir: '{output_dir}'\n", encoding="utf-8")


def test_output_dir_outside_root_is_a_config_error(tmp_path: Path) -> None:
    """`../../escaped` is refused with both the raw and the resolved path; nothing is written."""
    root = tmp_path / "a" / "project"
    root.mkdir(parents=True)
    _config(root, "../../escaped")

    result = CliRunner().invoke(cli, ["plan", "Add login.", "--root", str(root), "--no-input"])

    assert result.exit_code == 1
    assert "'../../escaped'" in result.output
    assert str((tmp_path / "escaped").resolve()) in result.output
    assert not (tmp_path / "escaped").exists()


def test_symlinked_output_dir_outside_root_is_refused(tmp_path: Path) -> None:
    """Symlinks are resolved before the check."""
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "docs").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not supported here")
    _config(root, "docs")

    result = CliRunner().invoke(cli, ["plan", "Add login.", "--root", str(root), "--no-input"])

    assert result.exit_code == 1
    assert "outside the project root" in result.output
    assert list(outside.iterdir()) == []


def test_verify_with_absolute_output_dir_inside_root(tmp_path: Path) -> None:
    """Guard: an absolute output_dir inside the root keeps working for plan and verify."""
    _config(tmp_path, str(tmp_path / "plans"))
    runner = CliRunner()

    planned = runner.invoke(cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input"])
    assert planned.exit_code == 0, planned.output

    verified = runner.invoke(cli, ["verify", "add-login", "--root", str(tmp_path)])

    assert verified.exit_code == 0, verified.output
    doc = (tmp_path / "plans" / "add-login-verify.md").read_text(encoding="utf-8")
    assert "[`plans/add-login-plan.md`](add-login-plan.md)" in doc


def test_verify_with_absolute_output_dir_outside_root(tmp_path: Path) -> None:
    """The original crash: verify raised an unhandled ValueError from relative_to."""
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "plans"
    outside.mkdir()
    (outside / "add-login-plan.md").write_text("# Feature: Add login.\n", encoding="utf-8")
    _config(root, str(outside))

    result = CliRunner().invoke(cli, ["verify", "add-login", "--root", str(root)])

    assert not isinstance(result.exception, ValueError), result.exception
    assert result.exit_code == 1
    assert "outside the project root" in result.output
    assert not (outside / "add-login-verify.md").exists()
