"""Tests for `template:` in .featuredoc.yml (custom plan templates)."""

from pathlib import Path

from click.testing import CliRunner, Result

from kingmadoc.cli import cli


def _plan(root: Path) -> Result:
    return CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(root), "--no-input", "--stdout"]
    )


def test_custom_template_from_config_is_used(tmp_path: Path) -> None:
    """An explicit template path renders with the plan context."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "plan.md.j2").write_text(
        "# {{ feature_summary }} ({{ project_name }})\n{{ c4_context }}\n", encoding="utf-8"
    )
    (tmp_path / ".featuredoc.yml").write_text(
        "template: ./docs/plan.md.j2\nproject: {name: Shop}\n", encoding="utf-8"
    )

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert result.stdout.startswith("# Add login. (Shop)\n```mermaid\nC4Context\n")


def test_bundled_name_selects_the_bundled_template(tmp_path: Path) -> None:
    """A bare bundled name loads the package template, even next to a same-named project file."""
    (tmp_path / "plan_default.md.j2").write_text("PROJECT COPY\n", encoding="utf-8")
    (tmp_path / ".featuredoc.yml").write_text("template: plan_default.md.j2\n", encoding="utf-8")

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert "PROJECT COPY" not in result.stdout
    # The bundled template: frontmatter, then the title.
    assert result.stdout.startswith("---\nkingmadoc: 1\n")
    assert "\n---\n# Feature: Add login.\n" in result.stdout


def test_configured_template_cannot_escape_the_sandbox(tmp_path: Path) -> None:
    """The fix 1 attack via an explicit template: blocked by the sandbox, nothing executed."""
    marker = tmp_path / "pwned"
    (tmp_path / "evil.md.j2").write_text(
        "{{ cycler.__init__.__globals__.os.system('touch " + marker.as_posix() + "') }}\n"
        "{{ ''.__class__.__mro__[1].__subclasses__() }}\n",
        encoding="utf-8",
    )
    (tmp_path / ".featuredoc.yml").write_text("template: ./evil.md.j2\n", encoding="utf-8")

    result = _plan(tmp_path)

    assert result.exit_code == 1
    assert "unsafe" in result.output
    assert not marker.exists()
