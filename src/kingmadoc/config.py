"""Loading and validation of `.featuredoc.yml`."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

from kingmadoc.exceptions import ConfigError

CONFIG_FILENAME = ".featuredoc.yml"

DEFAULT_EXCLUDE_DIRS: tuple[str, ...] = (
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "dist",
    "build",
    "*.egg-info",
)

# Hard ceiling on analyzed files, so huge repos cannot make `plan` run away.
MAX_FILES_LIMIT = 5000

SUPPORTED_DIAGRAMS: frozenset[str] = frozenset({"c4_context", "c4_container"})
# Must match kingmadoc.diagrams.BACKENDS (a test enforces it); config imports no diagrams.
DIAGRAM_FORMATS: tuple[str, ...] = ("mermaid", "plantuml", "d2")


@dataclass(frozen=True)
class ProjectConfig:
    """Project metadata used in generated documents."""

    name: str | None = None
    description: str = ""


@dataclass(frozen=True)
class AnalyzerConfig:
    """Settings for the codebase analyzer."""

    exclude_dirs: tuple[str, ...] = DEFAULT_EXCLUDE_DIRS
    max_files: int = MAX_FILES_LIMIT
    tree_depth: int = 3


@dataclass(frozen=True)
class ExtraDesignConfig:
    """One optional design doc written next to the plan doc."""

    enabled: bool = False


@dataclass(frozen=True)
class ExtraDesignsConfig:
    """Optional extra design documents (one field per doc type).

    ``functional_design`` and ``technical_design`` are written by ``plan``; ``adr``
    enables the ``kingmadoc adr`` command.
    """

    functional_design: ExtraDesignConfig = field(default_factory=ExtraDesignConfig)
    technical_design: ExtraDesignConfig = field(default_factory=ExtraDesignConfig)
    adr: ExtraDesignConfig = field(default_factory=ExtraDesignConfig)


@dataclass(frozen=True)
class FeatureDocConfig:
    """Complete KingmaDoc configuration."""

    output_dir: Path = Path("docs/features")
    template: str = "plan_default.md.j2"
    max_questions: int = 5
    project: ProjectConfig = field(default_factory=ProjectConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    diagrams: tuple[str, ...] = ("c4_context", "c4_container")
    diagram_format: str = "mermaid"
    extra_designs: ExtraDesignsConfig = field(default_factory=ExtraDesignsConfig)


def load_config(root: Path, config_path: Path | None = None) -> FeatureDocConfig:
    """Load configuration for the project at ``root``.

    Args:
        root: Project root directory.
        config_path: Explicit config file. If omitted, ``root/.featuredoc.yml`` is
            used when present; otherwise defaults are returned.

    Returns:
        The merged configuration (file values override defaults).

    Raises:
        ConfigError: If an explicit config file is missing, or the file is invalid.
    """
    if config_path is None:
        candidate = root / CONFIG_FILENAME
        if not candidate.is_file():
            return FeatureDocConfig()
        config_path = candidate
    elif not config_path.is_file():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot read {config_path}: {exc}") from exc

    return parse_config(raw if raw is not None else {})


def parse_config(data: Any) -> FeatureDocConfig:
    """Build a :class:`FeatureDocConfig` from parsed YAML data.

    Args:
        data: The top-level YAML mapping.

    Returns:
        The validated configuration.

    Raises:
        ConfigError: On unknown keys or values of the wrong type.
    """
    data = _require_mapping(data, "config")
    _reject_unknown(
        data,
        {
            "output_dir",
            "template",
            "max_questions",
            "project",
            "analyzer",
            "diagrams",
            "diagram_format",
            "extra_designs",
        },
        "config",
    )
    defaults = FeatureDocConfig()

    max_questions = _get(data, "max_questions", int, defaults.max_questions)
    if not 0 <= max_questions <= 5:
        raise ConfigError("max_questions must be between 0 and 5")

    diagrams = tuple(_get_str_list(data, "diagrams", defaults.diagrams))
    unsupported = set(diagrams) - SUPPORTED_DIAGRAMS
    if unsupported:
        raise ConfigError(
            f"Unsupported diagrams: {sorted(unsupported)}; "
            f"supported: {sorted(SUPPORTED_DIAGRAMS)}"
        )

    diagram_format = _get(data, "diagram_format", str, defaults.diagram_format)
    if diagram_format not in DIAGRAM_FORMATS:
        raise ConfigError(
            f"Unknown diagram_format {diagram_format!r}; supported: {', '.join(DIAGRAM_FORMATS)}"
        )

    return FeatureDocConfig(
        output_dir=Path(_get(data, "output_dir", str, str(defaults.output_dir))),
        template=_get(data, "template", str, defaults.template),
        max_questions=max_questions,
        project=_parse_project(data.get("project")),
        analyzer=_parse_analyzer(data.get("analyzer")),
        diagrams=diagrams,
        diagram_format=diagram_format,
        extra_designs=_parse_extra_designs(data.get("extra_designs")),
    )


def default_config_yaml() -> str:
    """Return the default `.featuredoc.yml` contents written by ``kingmadoc init``."""
    excludes = "\n".join(f"    - \"{name}\"" for name in DEFAULT_EXCLUDE_DIRS)
    return f"""\
# KingmaDoc configuration. All keys are optional; shown values are the defaults.

# Where generated feature docs are written (relative to the project root).
output_dir: docs/features

# Plan template: a bundled name, or an explicit path such as ./my_plan.md.j2
# (relative to the project root). Templates always run sandboxed.
template: plan_default.md.j2

# Number of clarifying questions asked in `plan` mode (0-5).
max_questions: 5

project:
  # Defaults to the project directory name.
  name: null
  description: ""

analyzer:
  max_files: {MAX_FILES_LIMIT}  # maximum
  tree_depth: 3
  exclude_dirs:
{excludes}

# Diagrams included in the plan doc.
diagrams:
  - c4_context
  - c4_container

# Diagram language: mermaid, plantuml (C4-PlantUML) or d2.
diagram_format: mermaid

# Optional extra documents.
extra_designs:
  functional_design:
    # <slug>-functional-design.md: user flows, edge cases, business rules,
    # permissions and roles.
    enabled: false
  technical_design:
    # <slug>-technical-design.md: database schema, API contracts, error handling,
    # performance and security considerations.
    enabled: false
  adr:
    # `kingmadoc adr "<title>"` writes docs/adr/<NNNN>-<slug>.md.
    enabled: false
"""


def _parse_project(data: Any) -> ProjectConfig:
    if data is None:
        return ProjectConfig()
    data = _require_mapping(data, "project")
    _reject_unknown(data, {"name", "description"}, "project")
    name = data.get("name")
    if name is not None and not isinstance(name, str):
        raise ConfigError("project.name must be a string or null")
    return ProjectConfig(
        name=name,
        description=_get(data, "description", str, "", "project."),
    )


def _parse_analyzer(data: Any) -> AnalyzerConfig:
    defaults = AnalyzerConfig()
    if data is None:
        return defaults
    data = _require_mapping(data, "analyzer")
    _reject_unknown(data, {"exclude_dirs", "max_files", "tree_depth"}, "analyzer")
    max_files = _get(data, "max_files", int, defaults.max_files, "analyzer.")
    tree_depth = _get(data, "tree_depth", int, defaults.tree_depth, "analyzer.")
    if not 1 <= max_files <= MAX_FILES_LIMIT:
        raise ConfigError(f"analyzer.max_files must be between 1 and {MAX_FILES_LIMIT}")
    if tree_depth < 1:
        raise ConfigError("analyzer.tree_depth must be >= 1")
    return AnalyzerConfig(
        exclude_dirs=tuple(
            _get_str_list(data, "exclude_dirs", defaults.exclude_dirs, "analyzer.")
        ),
        max_files=max_files,
        tree_depth=tree_depth,
    )


def _parse_extra_designs(data: Any) -> ExtraDesignsConfig:
    if data is None:
        return ExtraDesignsConfig()
    data = _require_mapping(data, "extra_designs")
    names = {f.name for f in fields(ExtraDesignsConfig)}
    _reject_unknown(data, names, "extra_designs")
    designs: dict[str, ExtraDesignConfig] = {}
    for name in names & set(data):
        where = f"extra_designs.{name}"
        entry = _require_mapping({} if data[name] is None else data[name], where)
        _reject_unknown(entry, {"enabled"}, where)
        designs[name] = ExtraDesignConfig(enabled=_get(entry, "enabled", bool, False, f"{where}."))
    return ExtraDesignsConfig(**designs)


def _require_mapping(data: Any, where: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a mapping, got {type(data).__name__}")
    return data


def _reject_unknown(data: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"Unknown keys in {where}: {sorted(unknown)}")


def _get(data: dict[str, Any], key: str, typ: type, default: Any, prefix: str = "") -> Any:
    value = data.get(key, default)
    # bool is a subclass of int; reject it explicitly for int fields.
    if not isinstance(value, typ) or (typ is int and isinstance(value, bool)):
        raise ConfigError(f"{prefix}{key} must be of type {typ.__name__}")
    return value


def _get_str_list(
    data: dict[str, Any], key: str, default: tuple[str, ...], prefix: str = ""
) -> list[str]:
    value = data.get(key, list(default))
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{prefix}{key} must be a list of strings")
    return value
