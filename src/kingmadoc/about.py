"""Which KingmaDoc build is installed (shown by ``kingmadoc --version``).

pip records how a package was installed (PEP 610, ``direct_url.json``): for a git install
that includes the commit, so an update is visible even when the version number is the
same.
"""

from __future__ import annotations

import json
from importlib import metadata
from typing import Any

from kingmadoc import __version__


def version_text() -> str:
    """Return the version, plus the git commit or ``editable`` when known.

    Returns:
        e.g. ``"0.2.0.dev0 (git 29244f7)"``, ``"0.2.0.dev0 (editable)"`` or ``"0.2.0.dev0"``.
    """
    try:
        raw = _distribution().read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return __version__
    if not raw:
        return __version__
    try:
        info: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        return __version__
    commit = info.get("vcs_info", {}).get("commit_id")
    if isinstance(commit, str) and commit:
        return f"{__version__} (git {commit[:7]})"
    if info.get("dir_info", {}).get("editable"):
        return f"{__version__} (editable)"
    return __version__


def _distribution() -> Any:
    return metadata.distribution("kingmadoc")
