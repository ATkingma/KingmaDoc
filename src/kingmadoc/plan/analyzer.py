"""Codebase analyzer: walks a repository (glob), reads manifests and scans sources (grep)."""

from __future__ import annotations

import json
import re
import tomllib
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from fnmatch import fnmatch
from itertools import islice
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from kingmadoc.config import MAX_FILES_LIMIT, AnalyzerConfig
from kingmadoc.exceptions import AnalysisError
from kingmadoc.plan.dependencies import Edge, module_dependencies

# Always skipped, even if the config's exclude_dirs leaves them out.
ALWAYS_EXCLUDED_DIRS: tuple[str, ...] = (
    ".git", "node_modules", ".venv", "__pycache__", "dist", "build",
    # Build output of Next.js and Nuxt, and SvelteKit's generated files.
    ".next", ".nuxt", ".svelte-kit",
)

# Config/marker file (name or glob) -> technology it indicates.
MARKER_FILES: Mapping[str, str] = MappingProxyType({
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "setup.cfg": "Python",
    "requirements.txt": "Python",
    "Pipfile": "Python",
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
    "docker-compose.yaml": "Docker Compose",
    "compose.yml": "Docker Compose",
    "compose.yaml": "Docker Compose",
})

# Manifests are only read near the root; deeper copies are usually fixtures or vendored code.
MAX_MARKER_DEPTH = 2

# File extension -> language key used in ``language_breakdown``.
EXTENSION_LANGUAGES: Mapping[str, str] = MappingProxyType({
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".swift": "swift",
    ".sh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "css",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".json": "json",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".j2": "jinja",
})

# Language key -> display name, for programming languages only (not docs or data).
SOURCE_LANGUAGES: Mapping[str, str] = MappingProxyType({
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "go": "Go",
    "rust": "Rust",
    "java": "Java",
    "kotlin": "Kotlin",
    "ruby": "Ruby",
    "php": "PHP",
    "csharp": "C#",
    "c": "C",
    "cpp": "C++",
    "swift": "Swift",
})

ENTRY_POINT_NAMES: frozenset[str] = frozenset({
    "main.py", "app.py", "__main__.py", "manage.py", "wsgi.py", "asgi.py", "server.py",
    "index.js", "index.ts", "index.tsx", "main.js", "main.ts", "main.tsx",
    "app.js", "app.ts", "server.js", "server.ts",
    "main.go", "main.rs", "Program.cs", "Main.java", "Main.kt",
})

TEST_DIR_NAMES: frozenset[str] = frozenset({"tests", "test", "__tests__", "spec", "specs"})

NPM_DEPENDENCY_KEYS: tuple[str, ...] = (
    "dependencies", "devDependencies", "peerDependencies", "optionalDependencies",
)
CARGO_DEPENDENCY_KEYS: tuple[str, ...] = ("dependencies", "dev-dependencies")

# Normalized dependency name (package, Go module, Docker image) -> technology.
DEPENDENCY_TECH: Mapping[str, str] = MappingProxyType({
    # Python
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "click": "Click",
    "typer": "Typer",
    "jinja2": "Jinja2",
    "pydantic": "Pydantic",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "psycopg": "PostgreSQL",
    "psycopg2": "PostgreSQL",
    "psycopg2-binary": "PostgreSQL",
    "asyncpg": "PostgreSQL",
    "pymysql": "MySQL",
    "mysqlclient": "MySQL",
    "pymongo": "MongoDB",
    "redis": "Redis",
    # JavaScript / TypeScript
    "react": "React",
    "next": "Next.js",
    "vue": "Vue",
    "svelte": "Svelte",
    "@angular/core": "Angular",
    "express": "Express",
    "@nestjs/core": "NestJS",
    "typescript": "TypeScript",
    "pg": "PostgreSQL",
    "mysql2": "MySQL",
    "mongoose": "MongoDB",
    "mongodb": "MongoDB",
    "ioredis": "Redis",
    "prisma": "Prisma",
    # Go
    "github.com/gin-gonic/gin": "Gin",
    "github.com/labstack/echo/v4": "Echo",
    "github.com/gofiber/fiber/v2": "Fiber",
    "gorm.io/gorm": "GORM",
    "github.com/lib/pq": "PostgreSQL",
    "github.com/jackc/pgx/v5": "PostgreSQL",
    "github.com/go-sql-driver/mysql": "MySQL",
    "github.com/redis/go-redis/v9": "Redis",
    # Rust
    "actix-web": "Actix Web",
    "axum": "Axum",
    "rocket": "Rocket",
    "tokio": "Tokio",
    "diesel": "Diesel",
    "sqlx": "SQLx",
    "tokio-postgres": "PostgreSQL",
    # Docker images
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgis": "PostgreSQL",
    "mysql": "MySQL",
    "mariadb": "MariaDB",
    "mongo": "MongoDB",
    "rabbitmq": "RabbitMQ",
    "elasticsearch": "Elasticsearch",
    "nginx": "nginx",
    "kafka": "Kafka",
    "cp-kafka": "Kafka",
})

# Framework -> (file suffixes to scan, import pattern). Python patterns use `[ \t]`, not
# `\s`: `^\s*` also matches newlines and backtracks quadratically over blank-line runs.
GREP_PATTERNS: Mapping[str, tuple[frozenset[str], re.Pattern[str]]] = MappingProxyType({
    name: (frozenset(suffixes), re.compile(pattern, re.MULTILINE))
    for name, suffixes, pattern in (
        ("Django", {".py"}, r"^[ \t]*(from|import)[ \t]+django\b"),
        ("Flask", {".py"}, r"^[ \t]*(from|import)[ \t]+flask\b"),
        ("FastAPI", {".py"}, r"^[ \t]*(from|import)[ \t]+fastapi\b"),
        ("Click", {".py"}, r"^[ \t]*(from|import)[ \t]+click\b"),
        ("SQLAlchemy", {".py"}, r"^[ \t]*(from|import)[ \t]+sqlalchemy\b"),
        ("Jinja2", {".py"}, r"^[ \t]*(from|import)[ \t]+jinja2\b"),
        ("PostgreSQL", {".py"}, r"^[ \t]*(from|import)[ \t]+(psycopg2?|asyncpg)\b"),
        ("React", {".js", ".jsx", ".ts", ".tsx"}, r"""from\s+['"]react['"]"""),
        ("Express", {".js", ".ts"}, r"""(require\(|from\s+)['"]express['"]"""),
    )
})

# Larger source files are almost always generated or vendored; skip them when grepping.
MAX_GREP_BYTES = 512 * 1024

NON_SOURCE_DIRS = frozenset({"tests", "test", "docs", "doc", "examples", "scripts", ".github"})


@dataclass(frozen=True)
class CodebaseReport:
    """Structured summary of a codebase.

    Attributes:
        root: Absolute project root.
        file_count: Number of files analyzed.
        language_breakdown: File count per language key (e.g. ``"python"``,
            ``"markdown"``), most common first.
        top_level_dirs: Directories directly under ``root`` that contain files, sorted.
        entry_points: Files that look like program entry points (relative, POSIX), sorted.
        config_files: Build/dependency/container config files (relative, POSIX), sorted.
        test_dirs: Outermost test directories (relative, POSIX), sorted.
        detected_stack: Languages, frameworks and services, sorted.
        files: Analyzed files, relative to ``root``, sorted.
        tree: Text rendering of the file tree (depth-limited).
        source_dirs: Directories that look like source modules (relative paths).
        truncated: True if the file limit was reached and the walk stopped early.
        module_dependencies: ``(importer, imported)`` edges between the project's own
            Python modules in the source directories, sorted; ``None`` if not computed
            (see ``with_dependencies``).
    """

    root: Path
    file_count: int
    language_breakdown: Mapping[str, int]
    top_level_dirs: tuple[str, ...]
    entry_points: tuple[str, ...]
    config_files: tuple[str, ...]
    test_dirs: tuple[str, ...]
    detected_stack: tuple[str, ...]
    files: tuple[Path, ...]
    tree: str
    source_dirs: tuple[Path, ...]
    truncated: bool
    module_dependencies: tuple[Edge, ...] | None = None

    @property
    def primary_language(self) -> str | None:
        """Display name of the programming language with the most files, if any."""
        return next(
            (SOURCE_LANGUAGES[k] for k in self.language_breakdown if k in SOURCE_LANGUAGES),
            None,
        )


def analyze(
    root: Path, config: AnalyzerConfig, *, with_dependencies: bool = False
) -> CodebaseReport:
    """Walk ``root`` and summarize its structure and technology.

    Args:
        root: Project root directory.
        config: Analyzer settings (excludes, limits).
        with_dependencies: Also build the Python module dependency graph. It parses every
            source file completely, so it is only done when asked for.

    Returns:
        A :class:`CodebaseReport`.

    Raises:
        AnalysisError: If ``root`` is not a directory.
    """
    root = root.resolve()
    if not root.is_dir():
        raise AnalysisError(f"Not a directory: {root}")

    limit = min(config.max_files, MAX_FILES_LIMIT)
    exclude = (*ALWAYS_EXCLUDED_DIRS, *config.exclude_dirs)
    files: list[Path] = []
    truncated = False
    for path in _iter_files(root, exclude):
        if len(files) >= limit:
            truncated = True
            break
        files.append(path.relative_to(root))
    files.sort()

    config_files = [f for f in files if _is_config_file(f)]
    languages = _count_languages(files)
    manifests = {f.as_posix(): _read_text(root / f) for f in config_files}
    stack = (
        {MARKER_FILES[p] for f in config_files for p in MARKER_FILES if fnmatch(f.name, p)}
        | {SOURCE_LANGUAGES[k] for k in languages if k in SOURCE_LANGUAGES}
        | detect_stack_from_manifests(manifests)
        | _grep_frameworks(root, files, config.max_lines_per_file)
    )

    source_dirs = _find_source_dirs(files)
    return CodebaseReport(
        root=root,
        file_count=len(files),
        language_breakdown=MappingProxyType(dict(languages.most_common())),
        top_level_dirs=tuple(sorted({f.parts[0] for f in files if len(f.parts) > 1})),
        entry_points=tuple(
            f.as_posix() for f in files if f.name in ENTRY_POINT_NAMES and not _in_test_dir(f)
        ),
        config_files=tuple(f.as_posix() for f in config_files),
        test_dirs=find_test_dirs(files),
        detected_stack=tuple(sorted(stack)),
        files=tuple(files),
        tree=render_tree(root.name, files, config.tree_depth),
        source_dirs=source_dirs,
        truncated=truncated,
        module_dependencies=(
            _python_dependencies(root, files, source_dirs) if with_dependencies else None
        ),
    )


def report_to_dict(report: CodebaseReport) -> dict[str, Any]:
    """Convert a report to JSON-serializable data (the output of ``analyze --json``).

    Args:
        report: Result of :func:`analyze`.

    Returns:
        A dict of plain strings, ints, bools, lists and dicts.
    """
    return {
        "root": str(report.root),
        "file_count": report.file_count,
        "language_breakdown": dict(report.language_breakdown),
        "top_level_dirs": list(report.top_level_dirs),
        "entry_points": list(report.entry_points),
        "config_files": list(report.config_files),
        "test_dirs": list(report.test_dirs),
        "detected_stack": list(report.detected_stack),
        "truncated": report.truncated,
        "module_dependencies": (
            None
            if report.module_dependencies is None
            else [list(edge) for edge in report.module_dependencies]
        ),
    }


def format_report(report: CodebaseReport) -> str:
    """Render a report as short human-readable text (the output of ``kingmadoc analyze``).

    Args:
        report: Result of :func:`analyze`.

    Returns:
        One ``Label: value`` line per field.
    """

    def items(values: Iterable[str]) -> str:
        return ", ".join(values) or "none"

    files = f"{report.file_count}" + (" (truncated)" if report.truncated else "")
    dependencies = (
        "not computed"
        if report.module_dependencies is None
        else f"{len(report.module_dependencies)} (Python imports)"
    )
    languages = (f"{name} {count}" for name, count in report.language_breakdown.items())
    return "\n".join([
        f"Root: {report.root}",
        f"Files: {files}",
        f"Languages: {items(languages)}",
        f"Top-level directories: {items(report.top_level_dirs)}",
        f"Entry points: {items(report.entry_points)}",
        f"Config files: {items(report.config_files)}",
        f"Test directories: {items(report.test_dirs)}",
        f"Detected stack: {items(report.detected_stack)}",
        f"Module dependencies: {dependencies}",
    ])


def detect_stack_from_manifests(manifests: Mapping[str, str]) -> set[str]:
    """Detect technologies from the dependencies declared in manifest files.

    Understands ``pyproject.toml``, ``requirements.txt``, ``package.json``, ``go.mod``,
    ``Cargo.toml`` and Docker Compose files. Unparseable files are ignored.

    Args:
        manifests: File path (only the name is used to pick a parser) -> file content.

    Returns:
        Technologies found in :data:`DEPENDENCY_TECH`.
    """
    found: set[str] = set()
    for path, text in manifests.items():
        found.update(
            DEPENDENCY_TECH[dep] for dep in _manifest_dependencies(Path(path).name, text)
            if dep in DEPENDENCY_TECH
        )
    return found


def find_test_dirs(files: Iterable[Path]) -> tuple[str, ...]:
    """Return the outermost directories named like test directories that contain files.

    Args:
        files: Relative file paths.

    Returns:
        Relative POSIX directory paths, sorted.
    """
    dirs: set[str] = set()
    for f in files:
        for i, part in enumerate(f.parts[:-1]):
            if part in TEST_DIR_NAMES:
                dirs.add(Path(*f.parts[: i + 1]).as_posix())
                break
    return tuple(sorted(dirs))


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
    tree: dict[str, Any] = {}  # nested: name -> subtree
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

    def walk(node: dict[str, Any], prefix: str) -> None:
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


def _read_text(path: Path) -> str:
    # utf-8-sig strips a byte-order mark (common on Windows), which json/tomllib reject.
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return ""


def _count_languages(files: Iterable[Path]) -> Counter[str]:
    return Counter(
        EXTENSION_LANGUAGES[f.suffix.lower()]
        for f in files
        if f.suffix.lower() in EXTENSION_LANGUAGES
    )


def _is_config_file(f: Path) -> bool:
    return len(f.parts) <= MAX_MARKER_DEPTH and any(fnmatch(f.name, p) for p in MARKER_FILES)


def _in_test_dir(f: Path) -> bool:
    return any(part in TEST_DIR_NAMES for part in f.parts[:-1])


def _manifest_dependencies(name: str, text: str) -> set[str]:
    """Return normalized dependency names declared in one manifest (empty if unknown).

    Every table and list is type-checked before use; anything of an unexpected type is
    skipped, so a malformed manifest never stops the analysis.
    """
    try:
        if name == "pyproject.toml":
            return _pyproject_dependencies(tomllib.loads(text))
        if name == "requirements.txt":
            return {_python_name(line) for line in text.splitlines()} - {""}
        if name == "package.json":
            data = _mapping(json.loads(text))
            return {
                dep.lower()
                for key in NPM_DEPENDENCY_KEYS
                for dep in _mapping(data.get(key))
            }
        if name == "go.mod":
            return set(re.findall(r"^\s*(?:require\s+)?([\w.-]+\.[\w/.-]+)\s+v", text, re.M))
        if name == "Cargo.toml":
            return _cargo_dependencies(tomllib.loads(text))
        if fnmatch(name, "*compose.y*ml"):
            services = _mapping(_mapping(yaml.safe_load(text)).get("services"))
            return {
                _image_name(service["image"])
                for service in services.values()
                if isinstance(service, dict) and isinstance(service.get("image"), str)
            }
    except (tomllib.TOMLDecodeError, json.JSONDecodeError, yaml.YAMLError):
        pass
    return set()


def _image_name(image: str) -> str:
    """``registry.local:5000/library/postgres:16`` or ``postgres@sha256:…`` -> ``postgres``."""
    # Path first: a registry host may contain a port ("host:5000/"), which is not a tag.
    last = image.split("@")[0].rsplit("/", 1)[-1]
    return last.split(":")[0].lower()


def _pyproject_dependencies(data: Mapping[str, Any]) -> set[str]:
    project = _mapping(data.get("project"))
    specs = _strings(project.get("dependencies"))
    for group in _mapping(project.get("optional-dependencies")).values():
        specs += _strings(group)
    # PEP 735; entries may also be {include-group = "..."} tables, which _strings skips.
    for group in _mapping(data.get("dependency-groups")).values():
        specs += _strings(group)
    poetry = _mapping(_mapping(data.get("tool")).get("poetry"))
    specs += list(_mapping(poetry.get("dependencies")))
    for group in _mapping(poetry.get("group")).values():
        specs += list(_mapping(_mapping(group).get("dependencies")))
    return {_python_name(spec) for spec in specs} - {"", "python"}


def _cargo_dependencies(data: Mapping[str, Any]) -> set[str]:
    tables = [data, _mapping(data.get("workspace")), *_mapping(data.get("target")).values()]
    return {
        dep.lower()
        for table in tables
        for key in CARGO_DEPENDENCY_KEYS
        for dep in _mapping(_mapping(table).get(key))
    }


def _strings(value: Any) -> list[str]:
    """The string items of a list; anything else (wrong type, nested tables) is skipped."""
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _python_name(spec: str) -> str:
    """Normalize a requirement spec (``"FastAPI[all]>=0.1"``) to ``"fastapi"``."""
    spec = spec.split("#")[0].strip()
    if not spec or spec.startswith("-"):
        return ""
    name = re.split(r"[\s<>=!~;\[@]", spec, maxsplit=1)[0]
    return name.lower().replace("_", "-")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _grep_frameworks(root: Path, files: list[Path], max_lines: int) -> set[str]:
    """Detect frameworks by scanning the first ``max_lines`` lines of source files.

    Files in test directories are skipped: what tests import is not the stack.
    """
    found: set[str] = set()
    for f in files:
        if _in_test_dir(f):
            continue
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
            with path.open(encoding="utf-8", errors="ignore") as handle:
                text = "".join(islice(handle, max_lines))
        except OSError:
            continue
        found.update(name for name, pattern in remaining.items() if pattern.search(text))
    return found


def _find_source_dirs(files: list[Path]) -> tuple[Path, ...]:
    """Find top-level source modules; descends one level into ``src/`` layouts.

    Test directories (:data:`TEST_DIR_NAMES`) are skipped at every level, including
    ``src/tests``. Loose files directly in ``src/`` count as a ``src`` module only when
    ``src/`` has no sub-packages.
    """
    dirs: set[Path] = set()
    loose_src = False
    for f in files:
        if EXTENSION_LANGUAGES.get(f.suffix.lower()) not in SOURCE_LANGUAGES or len(f.parts) < 2:
            continue
        top = f.parts[0]
        if top in NON_SOURCE_DIRS or top in TEST_DIR_NAMES or top.startswith("."):
            continue
        if top != "src":
            dirs.add(Path(top))
        elif len(f.parts) == 2:
            loose_src = True
        elif f.parts[1] not in TEST_DIR_NAMES and not f.parts[1].startswith("."):
            dirs.add(Path(top, f.parts[1]))
    if loose_src and not any(d.parts[0] == "src" for d in dirs):
        dirs.add(Path("src"))
    return tuple(sorted(dirs))


def _python_dependencies(
    root: Path, files: list[Path], source_dirs: tuple[Path, ...]
) -> tuple[Edge, ...]:
    """Read the Python files of the source directories and return their import edges."""
    sources: dict[Path, str] = {}
    for f in files:
        if f.suffix != ".py" or _in_test_dir(f):
            continue
        if not any(f.is_relative_to(d) for d in source_dirs):
            continue
        path = root / f
        try:
            if path.stat().st_size > MAX_GREP_BYTES:
                continue
        except OSError:
            continue
        sources[f] = _read_text(path)
    return module_dependencies(sources)
