"""Regression tests: templates from an untrusted project must never run code (fix 1)."""

from pathlib import Path

from click.testing import CliRunner, Result

from kingmadoc.cli import cli

# Classic Jinja server-side template injection: reaches `os` through a global and runs
# a shell command. Harmless payload; it only echoes a marker.
PAYLOAD = "{{ cycler.__init__.__globals__.os.popen('echo PWNED').read() }}\n"


def _plan(root: Path, *extra: str) -> Result:
    return CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(root), "--no-input", "--stdout", *extra]
    )


def test_template_in_project_root_is_ignored(tmp_path: Path) -> None:
    """A plan_default.md.j2 dropped in the repo root is not used; the bundled one is."""
    (tmp_path / "plan_default.md.j2").write_text(PAYLOAD, encoding="utf-8")

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert "PWNED" not in result.output
    # The bundled template: frontmatter, then the title.
    assert result.stdout.startswith("---\nkingmadoc: 1\n")
    assert "\n---\n# Feature: Add login.\n" in result.stdout
    assert "## One-sentence summary" in result.stdout


def test_explicit_template_is_sandboxed(tmp_path: Path) -> None:
    """Even an explicitly configured template cannot reach os/subprocess."""
    (tmp_path / "evil.md.j2").write_text(PAYLOAD, encoding="utf-8")
    (tmp_path / ".featuredoc.yml").write_text("template: ./evil.md.j2\n", encoding="utf-8")

    result = _plan(tmp_path)

    assert "PWNED" not in result.output
    assert result.exit_code == 1
    assert "evil.md.j2" in result.output


def test_configured_template_must_exist(tmp_path: Path) -> None:
    """A configured template path that does not exist is a config error."""
    (tmp_path / ".featuredoc.yml").write_text("template: ./missing.md.j2\n", encoding="utf-8")

    result = _plan(tmp_path)

    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_configured_template_must_be_a_file(tmp_path: Path) -> None:
    """A configured template path that is a directory is a config error."""
    (tmp_path / "templates").mkdir()
    (tmp_path / ".featuredoc.yml").write_text("template: ./templates\n", encoding="utf-8")

    result = _plan(tmp_path)

    assert result.exit_code == 1
    assert "not a file" in result.output
