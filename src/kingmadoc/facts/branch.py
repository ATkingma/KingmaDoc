"""What a branch changed compared with its base: its commits and the changed files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kingmadoc.exceptions import FactsError
from kingmadoc.git import run_git


@dataclass(frozen=True)
class ChangedFile:
    """A file the branch added (A), modified (M) or deleted (D), with its line counts."""

    status: str
    path: str
    added: int | None
    removed: int | None


@dataclass(frozen=True)
class BranchChanges:
    """The branch's commits since the merge base, oldest first, and its changed files."""

    base: str
    head: str
    merge_base: str
    commits: tuple[tuple[str, str], ...]
    files: tuple[ChangedFile, ...]


def branch_changes(root: Path, base: str) -> BranchChanges:
    """Compare the working tree (committed and uncommitted) with the merge base of ``base``.

    Args:
        root: Project root inside a git repository.
        base: The branch or commit the work started from, e.g. ``main``.

    Returns:
        The commits (``(hash, subject)``) and the changed files, sorted by path.

    Raises:
        FactsError: If this is not a git repository or git does not know ``base``.
    """
    if run_git(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}") is None:
        raise FactsError(f"git does not know {base!r} here (is {root} a git repository?)")
    merge_base = _required(root, "merge-base", base, "HEAD").strip()
    head = _required(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    log = _required(root, "log", "--reverse", "--format=%h%x09%s", f"{merge_base}..HEAD")
    commits = tuple(
        (sha, subject) for sha, _, subject in (line.partition("\t") for line in log.splitlines())
    )
    statuses = {
        path: status[0]
        for status, _, path in (
            line.partition("\t")
            for line in _required(root, "diff", "--no-renames", "--name-status", merge_base)
            .splitlines()
        )
    }
    counts: dict[str, tuple[int | None, int | None]] = {}
    for line in _required(root, "diff", "--no-renames", "--numstat", merge_base).splitlines():
        added, removed, path = line.split("\t", 2)
        counts[path] = (_count(added), _count(removed))
    files = tuple(
        ChangedFile(status, path, *counts.get(path, (None, None)))
        for path, status in sorted(statuses.items())
    )
    return BranchChanges(base, head, merge_base[:7], commits, files)


def _required(root: Path, *args: str) -> str:
    output = run_git(root, *args)
    if output is None:
        raise FactsError(f"git {' '.join(args[:2])} failed in {root}")
    return output


def _count(value: str) -> int | None:
    """numstat counts; ``-`` for binary files."""
    return int(value) if value.isdigit() else None
