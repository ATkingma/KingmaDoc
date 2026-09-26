"""Tests for `kingmadoc skills install`: the agent skills ship inside the package."""

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.skills import SKILL_NAMES, bundled_skill

REPO = Path(__file__).resolve().parents[1]
SOURCES = {
    "kingmadoc": REPO / "skill" / "SKILL.md",
    "explaining-code": REPO / "skill" / "explaining-code" / "SKILL.md",
}
TARGET_DIRS = {
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "codex": ".agents/skills",
    "copilot": ".github/skills",
}


def _install(root: Path, *extra: str) -> Result:
    return CliRunner().invoke(cli, ["skills", "install", "--root", str(root), *extra])


def test_bundled_skills_are_the_repository_skills() -> None:
    """The package ships exactly the skills from skill/ (no stale copies)."""
    assert set(SKILL_NAMES) == set(SOURCES)
    for name, source in SOURCES.items():
        assert bundled_skill(name).read_text(encoding="utf-8") == source.read_text(
            encoding="utf-8"
        )


@pytest.mark.parametrize("agent", list(TARGET_DIRS))
def test_installs_every_skill_for_each_agent(tmp_path: Path, agent: str) -> None:
    """Each agent gets both skills in its native skills directory, one folder per skill."""
    result = _install(tmp_path, "--agent", agent)

    assert result.exit_code == 0, result.output
    for name, source in SOURCES.items():
        target = tmp_path / TARGET_DIRS[agent] / name / "SKILL.md"
        assert target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
        assert str(target) in result.stdout


def test_default_agent_is_claude_code(tmp_path: Path) -> None:
    """Without --agent, the skills go to .claude/skills."""
    assert _install(tmp_path).exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "kingmadoc" / "SKILL.md").is_file()


def test_reinstall_is_a_no_op(tmp_path: Path) -> None:
    """Installing again when nothing changed succeeds and says it is up to date."""
    assert _install(tmp_path).exit_code == 0

    again = _install(tmp_path)

    assert again.exit_code == 0, again.output
    assert "up to date" in again.output


def test_local_changes_are_kept_unless_forced(tmp_path: Path) -> None:
    """An edited installed skill is not overwritten without --force."""
    assert _install(tmp_path).exit_code == 0
    target = tmp_path / ".claude" / "skills" / "explaining-code" / "SKILL.md"
    target.write_text("my edits", encoding="utf-8")

    refused = _install(tmp_path)
    assert refused.exit_code == 1
    assert "--force" in refused.output
    assert target.read_text(encoding="utf-8") == "my edits"

    forced = _install(tmp_path, "--force")
    assert forced.exit_code == 0, forced.output
    assert target.read_text(encoding="utf-8") == SOURCES["explaining-code"].read_text(
        encoding="utf-8"
    )


def test_unknown_agent_is_a_usage_error(tmp_path: Path) -> None:
    """Only the supported agents are accepted."""
    assert _install(tmp_path, "--agent", "emacs").exit_code == 2


def test_skill_folders_are_installed_completely(tmp_path: Path) -> None:
    """Every file of a skill folder (e.g. reference/*.md) is installed, not just SKILL.md."""
    folder = REPO / "skill" / "explaining-code"
    expected = sorted(p.relative_to(folder) for p in folder.rglob("*") if p.is_file())

    assert _install(tmp_path).exit_code == 0

    installed = tmp_path / ".claude" / "skills" / "explaining-code"
    files = [p for p in installed.rglob("*") if p.is_file()]
    assert sorted(p.relative_to(installed) for p in files) == expected
    for rel in expected:
        assert (installed / rel).read_bytes() == (folder / rel).read_bytes()
