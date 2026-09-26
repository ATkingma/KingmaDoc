"""Python module dependency graph from import statements (pure; roadmap WP9a).

Parses source with :mod:`ast` (no regexes, no imports executed) and keeps only imports
between the project's own modules: standard-library and third-party imports are not
part of the graph.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path

Edge = tuple[str, str]


def module_name(path: Path) -> str:
    """Return the dotted module name of a Python file (relative to the project root).

    A leading ``src/`` is not part of the name, and ``__init__.py`` names its package.

    Args:
        path: Relative path of a ``.py`` file.

    Returns:
        The dotted module name.

    Example:
        >>> module_name(Path("src/shop/api/__init__.py"))
        'shop.api'
    """
    parts = list(path.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def module_dependencies(sources: Mapping[Path, str]) -> tuple[Edge, ...]:
    """Return ``(importer, imported)`` edges between the given modules.

    Files that do not parse are skipped. Relative imports are resolved against the
    importing module's package.

    Args:
        sources: Relative ``.py`` path -> source text.

    Returns:
        Sorted, de-duplicated edges between the modules in ``sources``.
    """
    modules = {path: module_name(path) for path in sources}
    internal = set(modules.values())
    edges: set[Edge] = set()
    for path, text in sources.items():
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            continue
        source = modules[path]
        package = source.split(".") if path.name == "__init__.py" else source.split(".")[:-1]
        for candidates in _imported(tree, package):
            target = _resolve(candidates, internal)
            if target and target != source:
                edges.add((source, target))
    return tuple(sorted(edges))


def _imported(tree: ast.AST, package: Sequence[str]) -> list[list[list[str]]]:
    """Per imported name, the module paths it may refer to (most specific first)."""
    found: list[list[list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [[alias.name.split(".")] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                up = node.level - 1
                if up > len(package):
                    continue
                base = list(package[: len(package) - up])
            else:
                base = []
            base += node.module.split(".") if node.module else []
            found += [[[*base, alias.name], base] for alias in node.names]
    return found


def _resolve(candidates: list[list[str]], internal: set[str]) -> str | None:
    """The longest internal module that one of the candidate paths starts with."""
    for parts in candidates:
        for end in range(len(parts), 0, -1):
            name = ".".join(parts[:end])
            if name in internal:
                return name
    return None
