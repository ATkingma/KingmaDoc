"""JavaScript/TypeScript module dependencies from import statements (pure, roadmap WP9).

Only imports between the project's own files count: a relative path (``./x``,
``../y``) or a ``tsconfig.json``/``jsconfig.json`` ``paths`` alias (``@/components``).
Package imports (``react``) are left out.
"""

from __future__ import annotations

import json
import posixpath
import re
from collections.abc import Mapping

from kingmadoc.plan.dependencies import collapse

Edge = tuple[str, str]

SUFFIXES: tuple[str, ...] = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
CONFIG_FILES: tuple[str, ...] = ("tsconfig.json", "jsconfig.json")
# Above this many modules the graph is merged into folders (like the Python graph).
MAX_NODES = 25
_IMPORT = re.compile(
    r"""(?:\bimport\s[^'"`;]*?\bfrom\s*|\bimport\s*|\bexport\s[^'"`;]*?\bfrom\s*|"""
    r"""\brequire\(\s*|\bimport\(\s*)['"]([^'"]+)['"]"""
)


def js_dependencies(sources: Mapping[str, str], max_nodes: int = MAX_NODES) -> tuple[Edge, ...]:
    """Return ``(importer, imported)`` pairs between the project's JS/TS modules.

    Args:
        sources: Relative POSIX path -> text; JS/TS files and their tsconfig/jsconfig.
        max_nodes: Merge modules into folders above this many.

    Returns:
        Sorted edges between module paths without extension (``frontend/app/page``), or
        between folders when the graph was merged.
    """
    modules = {
        path: text for path, text in sources.items()
        if path.endswith(SUFFIXES) and not path.endswith(".d.ts")
    }
    names = {_strip(path): path for path in modules}
    aliases = _aliases(sources)
    edges: set[Edge] = set()
    for path, text in modules.items():
        importer = _strip(path)
        for spec in _IMPORT.findall(text):
            target = _resolve(spec, path, aliases, names)
            if target and target != importer:
                edges.add((importer, target))
    merged, _ = collapse(
        [(_dots(a), _dots(b)) for a, b in sorted(edges)], max_nodes=max_nodes
    )
    return tuple(sorted((_undots(a), _undots(b)) for a, b in merged))


def _resolve(
    spec: str, importer: str, aliases: list[tuple[str, str, str]], names: Mapping[str, str]
) -> str | None:
    if spec.startswith("."):
        base = posixpath.normpath(posixpath.join(posixpath.dirname(importer), spec))
    else:
        base = ""
        for scope, prefix, target in aliases:
            if spec.startswith(prefix) and importer.startswith(scope):
                base = posixpath.normpath(posixpath.join(target, spec[len(prefix):]))
                break
        if not base:
            return None
    for candidate in (_strip(base), f"{base}/index"):
        if candidate in names:
            return candidate
    return None


def _aliases(sources: Mapping[str, str]) -> list[tuple[str, str, str]]:
    """``(scope folder, import prefix, target folder)`` from every tsconfig/jsconfig."""
    found = []
    for path, text in sources.items():
        if posixpath.basename(path) not in CONFIG_FILES:
            continue
        folder = posixpath.dirname(path)
        options = _json(text).get("compilerOptions", {})
        if not isinstance(options, dict):
            continue
        base = posixpath.normpath(posixpath.join(folder, str(options.get("baseUrl", "."))))
        paths = options.get("paths", {})
        for pattern, targets in (paths.items() if isinstance(paths, dict) else []):
            if not (isinstance(targets, list) and targets and isinstance(targets[0], str)):
                continue
            prefix = pattern.removesuffix("*")
            target = posixpath.normpath(posixpath.join(base, targets[0].removesuffix("*")))
            scope = f"{folder}/" if folder else ""
            found.append((scope, prefix, target if target != "." else ""))
    # Longest prefix first, so "@/components/" wins over "@/".
    return sorted(found, key=lambda a: -len(a[1]))


def _json(text: str) -> dict[str, object]:
    """tsconfig allows comments and trailing commas; strip them before parsing."""
    cleaned = re.sub(r",\s*([}\]])", r"\1", _without_comments(text))
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _without_comments(text: str) -> str:
    """Drop // and /* */ comments outside JSON strings ("**/*.ts" is not a comment)."""
    out: list[str] = []
    i, in_string = 0, False
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if char == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 1
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            out.append(char)
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end == -1 else end + 2
            continue
        else:
            out.append(char)
        i += 1
    return "".join(out)


def _strip(path: str) -> str:
    for suffix in SUFFIXES:
        if path.endswith(suffix):
            return path[: -len(suffix)]
    return path


def _dots(path: str) -> str:
    """collapse() merges on "."; keep the dots in file names apart from the folders."""
    return path.replace(".", "\x00").replace("/", ".")


def _undots(name: str) -> str:
    return name.replace(".", "/").replace("\x00", ".")
