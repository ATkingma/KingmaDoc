"""Codebase analyzer: walks a repository (glob) and scans sources (grep) for hints."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from kingmadoc.config import AnalyzerConfig
from kingmadoc.exceptions import AnalysisError

# Marker file (name or glob) -> technology it indicates.
MARKER_FILES: dict[str, str] = {
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "requirements.txt": "Python",
    "package.json": "Node.js",
    "tsconfig.json": "TypeScript",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java (Maven)",
    "build.gradle": "JVM (Gradle)",
    "build.gradle.kts": "JVM (Gradle)",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "*.csproj": ".NET",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "compose.yaml": "Docker Compose",
}

EXTENSION_LANGUAGES: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".c": "C",
    ".cpp": "C++",
    ".swift": "Swift",
}

# Framework -> (file suffixes to scan, pattern).
GREP_PATTERNS: dict[str, tuple[frozenset[str], re.Pattern[str]]] = {
    name: (frozenset(suffixes), re.compile(pattern, re.MULTILINE))
    for name, suffixes, pattern in (
        ("Django", {".py"}, r"^\s*(from|import)\s+django\b"),
        ("Flask", {".py"}, r"^\s*(from|import)\s+flask\b"),
        ("FastAPI", {".py"}, r"^\s*(from|import)\s+fastapi\b"),
        ("Click", {".py"}, r"^\s*(from|import)\s+click\b"),
        ("SQLAlchemy", {".py"}, r"^\s*(from|import)\s+sqlalchemy\b"),
        ("Jinja2", {".py"}, r"^\s*(from|import)\s+jinja2\b"),
        ("React", {".js", ".jsx", ".ts", ".tsx"}, r"""from\s+['"]react['"]"""),
        ("Express", {".js", ".ts"}, r"""(require\(|from\s+)['"]express['"]"""),
    )
}

MAX_GREP_BYTES = 512 * 1024


@dataclass(frozen=True)
class AnalysisResult:
    """Summary of a codebase.

    Attributes:
        root: Absolute project root.
        files: Discovered files, relative to ``root``, sorted.
        tree: Text rendering of the file tree (depth-limited).
        languages: Source file count per language, most common first.
        tech_stack: Detected technologies and frameworks, sorted.
        source_dirs: Directories that look like source modules (relative paths).
        truncated: True if ``max_files`` was reached and the walk stopped early.
    """

    root: Path
    files: tuple[Path, ...]
    tree: str
    languages: dict[str, int]
    tech_stack: tuple[str, ...]
    source_dirs: tuple[Path, ...]
    truncated: bool

    @property
    def primary_language(self) -> str | None:
        """The language with the most source files, if any."""
        return next(iter(self.languages), None)


def analyze(root: Path, config: AnalyzerConfig) -> AnalysisResult:
    """Walk ``root`` and summarize its structure and technology.

    Args:
        root: Project root directory.
        config: Analyzer settings (excludes, limits).

    Returns:
        An :class:`AnalysisResult`.

    Raises:
        AnalysisError: If ``root`` is not a directory.
    """
    root = root.resolve()
    if not root.is_dir():
        raise AnalysisError(f"Not a directory: {root}")

    files: list[Path] = []
    truncated = False
    for path in _iter_files(root, config.exclude_dirs):
        if len(files) >= config.max_files:
            truncated = True
            break
        files.append(path.relative_to(root))
    files.sort()

    languages = Counter(
        EXTENSION_LANGUAGES[f.suffix] for f in files if f.suffix in EXTENSION_LANGUAGES
    )
    tech = _detect_markers(files) | _grep_frameworks(root, files)

    return AnalysisResult(
        root=root,
        files=tuple(files),
        tree=render_tree(root.name, files, config.tree_depth),
        languages=dict(languages.most_common()),
        tech_stack=tuple(sorted(tech)),
        source_dirs=_find_source_dirs(files),
        truncated=truncated,
    )


def render_tree(root_name: str, files: list[Path], depth: int) -> str:
    """Render relative file paths as an indented tree, collapsing below ``depth``.

    Args:
        root_name: Label for the root node.
        files: Relative file paths.
        depth: Maximum number of named path components to show; anything deeper
            is collapsed into a single ``…`` entry under its directory.

    Returns:
        A multi-line tree string.
    """
    tree: dict[str, dict] = {}
    for f in files:
        node = tree
        parts = f.parts
        for part in parts[:depth] if len(parts) > depth else parts[:-1]:
            node = node.setdefault(part + "/", {})
        if len(parts) > depth:
            node.setdefault("…", {})
        else:
            node.setdefault(parts[-1], {})

    lines = [f"{root_name}/"]

    def walk(node: dict[str, dict], prefix: str) -> None:
        # Directories first, then files; "…" marker last.
        keys = sorted(node, key=lambda k: (k == "…", not k.endswith("/"), k.lower()))
        for i, key in enumerate(keys):
            last = i == len(keys) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{key}")
            walk(node[key], prefix + ("    " if last else "│   "))

    walk(tree, "")
    return "\n".join(lines)


def _iter_files(root: Path, exclude: tuple[str, ...]) -> Iterator[Path]:
    """Yield regular files under ``root``, skipping excluded dirs and symlinks."""
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            continue
        subdirs: list[Path] = []
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if not any(fnmatch(entry.name, pattern) for pattern in exclude):
                    subdirs.append(entry)
            elif entry.is_file():
                yield entry
        # Reverse so directories are visited in sorted order.
        stack.extend(reversed(subdirs))


def _detect_markers(files: list[Path]) -> set[str]:
    """Detect technologies from marker files at the top two levels."""
    found: set[str] = set()
    for f in files:
        if len(f.parts) > 2:
            continue
        for pattern, tech in MARKER_FILES.items():
            if fnmatch(f.name, pattern):
                found.add(tech)
    return found


def _grep_frameworks(root: Path, files: list[Path]) -> set[str]:
    """Detect frameworks by scanning source files for import patterns."""
    found: set[str] = set()
    for f in files:
        remaining = {
            name: pattern
            for name, (suffixes, pattern) in GREP_PATTERNS.items()
            if name not in found and f.suffix in suffixes
        }
        if not remaining:
            continue
        path = root / f
        try:
            if path.stat().st_size > MAX_GREP_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        found.update(name for name, pattern in remaining.items() if pattern.search(text))
    return found


NON_SOURCE_DIRS = frozenset({"tests", "test", "docs", "doc", "examples", "scripts", ".github"})


def _find_source_dirs(files: list[Path]) -> tuple[Path, ...]:
    """Find top-level source modules; descends one level into ``src/`` layouts."""
    dirs: set[Path] = set()
    for f in files:
        if f.suffix not in EXTENSION_LANGUAGES or len(f.parts) < 2:
            continue
        top = f.parts[0]
        if top in NON_SOURCE_DIRS or top.startswith("."):
            continue
        if top == "src" and len(f.parts) >= 3:
            dirs.add(Path(top, f.parts[1]))
        else:
            dirs.add(Path(top))
    return tuple(sorted(dirs))
