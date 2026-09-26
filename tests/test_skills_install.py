"""Tests for `kingmadoc skills install`: the agent skills ship inside the package."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc import skills
from kingmadoc.cli import cli
from kingmadoc.skills import MANIFEST, SKILL_NAMES, bundled_skill

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
    files = [p for p in installed.rglob("*") if p.is_file() and p.name != MANIFEST]
    assert sorted(p.relative_to(installed) for p in files) == expected
    for rel in expected:
        assert (installed / rel).read_bytes() == (folder / rel).read_bytes()


def _skill_md(root: Path) -> Path:
    return root / ".claude" / "skills" / "explaining-code" / "SKILL.md"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_an_older_installed_version_is_updated_without_force(tmp_path: Path) -> None:
    """A file still as an earlier install left it is not a local edit: it is replaced."""
    assert _install(tmp_path).exit_code == 0
    target = _skill_md(tmp_path)
    manifest = target.parent / MANIFEST
    target.write_text("skill as KingmaDoc 0.1 shipped it", encoding="utf-8")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["files"]["SKILL.md"] = _sha("skill as KingmaDoc 0.1 shipped it")
    manifest.write_text(json.dumps(data), encoding="utf-8")

    result = _install(tmp_path)

    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") == SOURCES["explaining-code"].read_text(
        encoding="utf-8"
    )


def test_installs_from_before_the_manifest_are_recognised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a manifest, a file matching a previously shipped version is replaced."""
    old = "explaining-code 3.0 as it was shipped"
    history = {**skills.PREVIOUS_RELEASES, "explaining-code/SKILL.md": frozenset({_sha(old)})}
    monkeypatch.setattr(skills, "PREVIOUS_RELEASES", history)
    _skill_md(tmp_path).parent.mkdir(parents=True)
    _skill_md(tmp_path).write_text(old, encoding="utf-8")

    result = _install(tmp_path)

    assert result.exit_code == 0, result.output
    assert _skill_md(tmp_path).read_text(encoding="utf-8") != old


def test_previous_releases_cover_every_released_skill_version() -> None:
    """The frozen history holds the version installed from commit 29244f7 (pre-manifest)."""
    shown = subprocess.run(
        ["git", "-C", str(REPO), "show", "29244f7:skill/explaining-code/SKILL.md"],
        capture_output=True, check=False,
    )
    if shown.returncode != 0:
        pytest.skip("git history not available (shallow clone)")
    text = shown.stdout.decode("utf-8").replace("\r\n", "\n")

    assert _sha(text) in skills.PREVIOUS_RELEASES["explaining-code/SKILL.md"]


def test_a_file_the_skill_no_longer_ships_is_removed_when_unchanged(tmp_path: Path) -> None:
    """Files an earlier version installed but the current one dropped are cleaned up."""
    assert _install(tmp_path).exit_code == 0
    folder = _skill_md(tmp_path).parent
    (folder / "reference" / "old.md").write_text("old", encoding="utf-8")
    (folder / "reference" / "mine.md").write_text("edited", encoding="utf-8")
    data = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    data["files"]["reference/old.md"] = _sha("old")
    data["files"]["reference/mine.md"] = _sha("as shipped")
    (folder / MANIFEST).write_text(json.dumps(data), encoding="utf-8")

    result = _install(tmp_path)

    assert result.exit_code == 0, result.output
    assert not (folder / "reference" / "old.md").exists()
    assert (folder / "reference" / "mine.md").read_text(encoding="utf-8") == "edited"


@pytest.mark.parametrize("key", ["../../../outside.txt", "reference/../../../outside.txt"])
def test_a_manifest_cannot_remove_files_outside_the_skill(tmp_path: Path, key: str) -> None:
    """The manifest is repository content: its paths never reach outside the skill folder."""
    assert _install(tmp_path).exit_code == 0
    folder = _skill_md(tmp_path).parent
    outside = tmp_path / "outside.txt"
    outside.write_text("keep me", encoding="utf-8")
    data = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    data["files"][key] = _sha("keep me")
    data["files"][str(outside)] = _sha("keep me")
    (folder / MANIFEST).write_text(json.dumps(data), encoding="utf-8")

    result = _install(tmp_path)

    assert result.exit_code == 0, result.output
    assert outside.read_text(encoding="utf-8") == "keep me"


def test_a_corrupt_manifest_is_treated_as_missing(tmp_path: Path) -> None:
    """An unreadable manifest does not crash the install; unchanged files are rewritten."""
    assert _install(tmp_path).exit_code == 0
    folder = _skill_md(tmp_path).parent
    (folder / MANIFEST).write_text("{not json", encoding="utf-8")

    result = _install(tmp_path)

    assert result.exit_code == 0, result.output
    assert json.loads((folder / MANIFEST).read_text(encoding="utf-8"))["skill"] == (
        "explaining-code"
    )
