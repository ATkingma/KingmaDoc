"""Tests for `kingmadoc explain status`: which explainers the code has moved away from."""

import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.explain import EXPLAIN_DIR, based_on_commit, freshness, referenced_paths

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

EXPLAINER = """\
# Checkout: architecture explained

| | |
| --- | --- |
| **Scope** | feature |
| **Based on** | {commit} · 2026-09-26 · KingmaDoc skill explaining-code 5.2.0 (arc42) |

## Where to find what

| What | Where |
| --- | --- |
| Cart | `src/cart.py` |
| Payment | `src/pay/` (see `src/pay/stripe.py:12`) |
| Not a path | `kingmadoc render` |
"""


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    """A repository with src/cart.py, src/pay/stripe.py and src/other.py; returns HEAD."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    for name in ("src/cart.py", "src/pay/stripe.py", "src/other.py"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path, _git(tmp_path, "rev-parse", "--short", "HEAD")


def _explainer(root: Path, commit: str, folder: str = "0001-checkout") -> Path:
    doc = root / EXPLAIN_DIR / folder / "README.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(EXPLAINER.format(commit=commit), encoding="utf-8")
    return doc


def _status(root: Path, *extra: str) -> Result:
    return CliRunner().invoke(cli, ["explain", "status", "--root", str(root), *extra])


def test_based_on_commit_is_read_from_the_header() -> None:
    """The commit in the **Based on** row, not a date or a version."""
    assert based_on_commit(EXPLAINER.format(commit="29244f7")) == "29244f7"
    assert based_on_commit("# No header\n") is None


def test_referenced_paths_are_the_existing_files_and_folders(tmp_path: Path) -> None:
    """Backticked paths that exist, without :line suffixes; commands are ignored."""
    root, _ = _repo(tmp_path)

    paths = referenced_paths(EXPLAINER.format(commit="abc1234"), root)

    assert paths == ["src/cart.py", "src/pay", "src/pay/stripe.py"]


def test_up_to_date_when_nothing_it_explains_changed(tmp_path: Path) -> None:
    """A change elsewhere in the project does not make the explainer outdated."""
    root, commit = _repo(tmp_path)
    doc = _explainer(root, commit)
    (root / "src" / "other.py").write_text("x = 2\n", encoding="utf-8")

    result = freshness(root, doc.parent)

    assert result.commit == commit and result.changed == () and result.problem is None


def test_outdated_lists_the_changed_files(tmp_path: Path) -> None:
    """Committed and uncommitted changes to explained files both count."""
    root, commit = _repo(tmp_path)
    doc = _explainer(root, commit)
    (root / "src" / "pay" / "stripe.py").write_text("x = 2\n", encoding="utf-8")
    _git(root, "commit", "-qam", "change stripe")
    (root / "src" / "cart.py").write_text("x = 3\n", encoding="utf-8")

    result = freshness(root, doc.parent)

    assert result.changed == ("src/cart.py", "src/pay/stripe.py")


def test_without_paths_the_whole_project_counts(tmp_path: Path) -> None:
    """An explainer that names no files is compared against the whole project."""
    root, commit = _repo(tmp_path)
    doc = root / EXPLAIN_DIR / "0001-all" / "README.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(f"# All\n\n| **Based on** | {commit} · 2026-09-26 |\n", encoding="utf-8")
    (root / "src" / "other.py").write_text("x = 2\n", encoding="utf-8")

    result = freshness(root, doc.parent)

    assert result.whole_project and result.changed == ("src/other.py",)


def test_changes_to_the_explainer_itself_do_not_count(tmp_path: Path) -> None:
    """Committing the explainer (docs/explain/) is not a change to the explained code."""
    root, commit = _repo(tmp_path)
    doc = root / EXPLAIN_DIR / "0001-all" / "README.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(f"# All\n\n| **Based on** | {commit} · 2026-09-26 |\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "add explainer")

    assert freshness(root, doc.parent).changed == ()


def test_unknown_or_missing_commit_is_reported(tmp_path: Path) -> None:
    """No **Based on** commit, or one git does not know, is a problem, not a crash."""
    root, _ = _repo(tmp_path)
    missing = _explainer(root, "", "0001-missing")
    unknown = _explainer(root, "deadbee", "0002-unknown")

    assert "no commit" in (freshness(root, missing.parent).problem or "")
    assert "deadbee" in (freshness(root, unknown.parent).problem or "")


def test_cli_status_and_check(tmp_path: Path) -> None:
    """One line per explainer; --check exits 1 when one is outdated (for CI)."""
    root, commit = _repo(tmp_path)
    _explainer(root, commit)
    fresh = _status(root, "--check")
    (root / "src" / "cart.py").write_text("x = 2\n", encoding="utf-8")

    stale = _status(root)
    stale_check = _status(root, "--check")

    assert fresh.exit_code == 0, fresh.output
    assert "0001" in fresh.output and "up to date" in fresh.output
    assert stale.exit_code == 0 and "1 file changed" in stale.output
    assert "src/cart.py" in stale.output
    assert stale_check.exit_code == 1


def test_cli_status_without_explainers(tmp_path: Path) -> None:
    """No docs/explain/ yet: say so."""
    result = _status(tmp_path)

    assert result.exit_code == 0 and "No explainers" in result.output
