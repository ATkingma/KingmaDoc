"""Running git read-only in the project (for explainer status and branch facts)."""

from __future__ import annotations

import subprocess
from pathlib import Path

GIT_TIMEOUT = 30


def run_git(root: Path, *args: str) -> str | None:
    """Run ``git -C root <args>`` and return its output.

    Args:
        root: Directory inside the repository.
        *args: The git command and its arguments.

    Returns:
        Standard output, or None when git is missing, times out or fails.
    """
    try:
        done = subprocess.run(  # noqa: S603 - fixed program, no shell
            ["git", "-C", str(root), *args],  # noqa: S607 - git from PATH, like the user's
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def short_head(root: Path) -> str | None:
    """Return the abbreviated commit hash of HEAD, or None outside a repository.

    Args:
        root: Directory inside the repository.

    Returns:
        E.g. ``"a2b27bc"``.
    """
    output = run_git(root, "rev-parse", "--short", "HEAD")
    return output.strip() if output else None
