"""Tests for finding the plan in ``kingmadoc verify`` (slugs, missing plans, output)."""

from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli


def _plan(root: Path, slug: str = "add-login") -> Path:
    path = root / "docs" / "features" / f"{slug}-plan.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Feature: Add login.\n", encoding="utf-8")
    return path


def test_missing_plan_exits_1(tmp_path: Path) -> None:
    """No plan doc: exit code 1, a clear error, and nothing written."""
    result = CliRunner().invoke(cli, ["verify", "add-login", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "No plan doc found" in result.output
    assert "add-login-plan.md" in result.output
    assert "kingmadoc plan" in result.output
    assert not (tmp_path / "docs").exists()


def test_missing_plan_lists_available_slugs(tmp_path: Path) -> None:
    """A typo in the slug shows which plans do exist."""
    _plan(tmp_path, "add-login")

    result = CliRunner().invoke(cli, ["verify", "add-logn", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Available: add-login" in result.output


def test_invalid_slug_exits_1(tmp_path: Path) -> None:
    """Slugs that are paths (or not kebab-case) are rejected before touching disk."""
    for slug in ("../secrets", "Add Login", "add-login-plan.md"):
        result = CliRunner().invoke(cli, ["verify", slug, "--root", str(tmp_path)])

        assert result.exit_code == 1, slug
        assert "Invalid feature slug" in result.output


def test_existing_plan_creates_verify_doc(tmp_path: Path) -> None:
    """With a plan doc, the verification doc is written next to it."""
    _plan(tmp_path)

    result = CliRunner().invoke(cli, ["verify", "add-login", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    path = tmp_path / "docs" / "features" / "add-login-verify.md"
    assert result.stdout.strip() == str(path)
    doc = path.read_text(encoding="utf-8")
    assert doc.startswith("# Verification: add-login\n")
    assert "[`docs/features/add-login-plan.md`](add-login-plan.md)" in doc


def test_existing_verify_doc_needs_force(tmp_path: Path) -> None:
    """A second run does not overwrite the verification doc without --force."""
    _plan(tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["verify", "add-login", "--root", str(tmp_path)]).exit_code == 0

    again = runner.invoke(cli, ["verify", "add-login", "--root", str(tmp_path)])
    forced = runner.invoke(cli, ["verify", "add-login", "--root", str(tmp_path), "--force"])

    assert again.exit_code == 1 and "--force" in again.output
    assert forced.exit_code == 0, forced.output
