"""Dependencies between the projects of a solution, read from their manifests."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath

Edge = tuple[str, str]

PROJECT_SUFFIXES = (".csproj", ".fsproj", ".vbproj")
_REFERENCE = re.compile(r"<ProjectReference\s+Include\s*=\s*\"([^\"]+)\"")


def project_references(manifests: Mapping[str, str]) -> tuple[Edge, ...]:
    """Return the ``(project, referenced project)`` pairs of .NET project files.

    Args:
        manifests: Relative POSIX path -> text, for any manifest files; only
            ``.csproj``/``.fsproj``/``.vbproj`` are read.

    Returns:
        Sorted, unique pairs of project names (the file name without its suffix).
    """
    edges: set[Edge] = set()
    for path, text in manifests.items():
        if not path.endswith(PROJECT_SUFFIXES):
            continue
        source = PurePosixPath(path).stem
        for include in _REFERENCE.findall(text):
            target = PurePosixPath(include.replace("\\", "/")).stem
            if target and target != source:
                edges.add((source, target))
    return tuple(sorted(edges))
