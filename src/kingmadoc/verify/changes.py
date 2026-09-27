"""What changed in the project since its plan was written (git)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from kingmadoc.git import run_git

# git's empty tree: the base when the plan is older than the first commit.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


@dataclass(frozen=True)
class Changes:
    """Files changed since the plan (committed, uncommitted, untracked) and the commits.

    Attributes:
        base: The last commit before the plan was generated ("" when there is none).
        files: Changed paths relative to the project root, sorted.
        messages: The commit messages since ``base``.
        problem: Why changes could not be detected (None when they were).
    """

    base: str | None
    files: tuple[str, ...]
    messages: str
    problem: str | None


def detect_changes(
    root: Path, since: datetime | None, ignore: tuple[str, ...], plan: str | None = None
) -> Changes:
    """Compare the working tree with the state the plan was written against.

    That state is the parent of the commit that added the plan (``plan``), or, while the
    plan is not committed, the last commit before ``since``. **Generated** is to the
    minute, so a commit within that minute still counts as before the plan.

    Args:
        root: Project root inside a git repository.
        since: When the plan was generated.
        ignore: Path prefixes that never count (the plan and verify docs themselves).
        plan: The plan's path relative to ``root``.

    Returns:
        The changes, or a :class:`Changes` with ``problem`` set.
    """
    if since is None:
        return Changes(None, (), "", "the plan has no **Generated** date and time")
    if run_git(root, "rev-parse", "--is-inside-work-tree") is None:
        return Changes(None, (), "", f"{root} is not a git repository")
    base = _plan_parent(root, plan) if plan else None
    if base is None:
        before = (since + timedelta(seconds=59)).isoformat()
        base = (run_git(root, "rev-list", "-1", f"--before={before}", "HEAD") or "").strip()
    against = base or EMPTY_TREE
    diff = run_git(root, "diff", "--relative", "--name-only", against)
    untracked = run_git(root, "ls-files", "--others", "--exclude-standard")
    history = f"{base}..HEAD" if base else "HEAD"
    messages = run_git(root, "log", "--format=%B", history) or ""
    if diff is None or untracked is None:
        return Changes(base, (), messages, "git could not compare the working tree")
    files = {
        line.strip()
        for line in (diff + untracked).splitlines()
        if line.strip() and not line.strip().startswith(ignore)
    }
    return Changes(base[:7] if base else "", tuple(sorted(files)), messages, None)


def _plan_parent(root: Path, plan: str) -> str | None:
    """The parent of the commit that first added ``plan`` ("" if that was the first
    commit); None when the plan is not committed."""
    added = run_git(root, "log", "--diff-filter=A", "--format=%H", "--", plan)
    commits = (added or "").split()
    if not commits:
        return None
    parent = run_git(root, "rev-parse", "--verify", "--quiet", f"{commits[-1]}^")
    return (parent or "").strip()
