"""Loading and validation of `.featuredoc.yml`."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from types import MappingProxyType
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

SUPPORTED_DIAGRAMS: frozenset[str] = frozenset({"c4_context", "c4_container", "class", "sequence"})
# How the skill embeds a rendered PNG below each Mermaid block (the CLI writes none).
DIAGRAMS_PNG_MODES: tuple[str, ...] = ("embed", "file", "off")
# Models each extra design document can contain, in document order. Must match the
# renderers in kingmadoc.plan.models (checked when that module is imported).
DOCUMENT_MODELS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "functional_design": (
        "user_stories", "use_case_diagram", "use_cases", "screen_designs",
        "evil_user_stories", "user_flows",
    ),
    "domain_design": ("domain_model", "event_storming"),
    "technical_design": (
        "business_rules", "permissions", "edge_cases", "threat_model", "dependency_graph",
    ),
    "security_design": ("threat_model", "permissions"),
})

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
    max_lines_per_file: int = 2000


@dataclass(frozen=True)
class ExtraDesignConfig:
    """One optional design doc written next to the plan doc.

    Attributes:
        enabled: Write this document on ``plan``.
        template: Bundled template name, or an explicit path relative to the project root.
        models: Design models to include, in order (see :data:`DOCUMENT_MODELS`).
    """

    enabled: bool = False
    template: str = ""
    models: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtraDesignsConfig:
    """Optional extra design documents written by ``plan`` (one field per doc type).

    Every field needs a matching entry in ``kingmadoc.plan.generator.EXTRA_DESIGNS``;
    the generator checks this when it is imported.
    """

    functional_design: ExtraDesignConfig = field(
        default_factory=lambda: _design("functional_design")
    )
    domain_design: ExtraDesignConfig = field(default_factory=lambda: _design("domain_design"))
    technical_design: ExtraDesignConfig = field(
        default_factory=lambda: _design("technical_design")
    )
    security_design: ExtraDesignConfig = field(
        default_factory=lambda: _design("security_design")
    )


def _design(name: str) -> ExtraDesignConfig:
    """Defaults for one extra design: its bundled template and all of its models."""
    return ExtraDesignConfig(template=f"{name}.md.j2", models=DOCUMENT_MODELS[name])


# Explainer formats of the `explaining-code` skill: arc42 (the 12 arc42 sections, default)
# or c4 (a compact zoom-in: context, containers, components, flows, data).
EXPLAIN_FORMATS: tuple[str, ...] = ("arc42", "c4")
# One explainer per subject (default), or split into a functional and a technical one.
# "functional" / "technical" write only the functional (FO) or technical (TO) document.
EXPLAIN_DOCUMENTS: tuple[str, ...] = ("single", "split", "functional", "technical")
# Models the explaining-code skill may draw (default: all; each only when the code has
# its signal). Names match the sections of its reference files.
EXPLAIN_MODELS: tuple[str, ...] = (
    "c4_context", "c4_container", "c4_component", "c4_code", "c4_deployment", "c4_dynamic",
    "sequence", "state_machine", "er_diagram", "domain_model", "class_diagram",
    "package_diagram", "activity", "user_journey", "use_case", "event_flow", "context_map",
    "data_flow", "algorithm", "user_stories", "screens", "evil_user_stories", "threat_model",
)


@dataclass(frozen=True)
class ExplainConfig:
    """Explainers written by the `explaining-code` agent skill.

    Attributes:
        format: One of :data:`EXPLAIN_FORMATS`.
        documents: One of :data:`EXPLAIN_DOCUMENTS`.
        models: Models the skill may draw, from :data:`EXPLAIN_MODELS` (default: all).
    """

    format: str = "arc42"
    documents: str = "single"
    models: tuple[str, ...] = EXPLAIN_MODELS


@dataclass(frozen=True)
class VerifyConfig:
    """Checks run by ``kingmadoc verify --run-checks``.

    Attributes:
        build: Build command; None: detected from the project files.
        test: Test command; None: detected.
        lint: Lint command; None: detected.
        timeout: Seconds each command may run.
    """

    build: str | None = None
    test: str | None = None
    lint: str | None = None
    timeout: int = 600


@dataclass(frozen=True)
class AdrConfig:
    """Architecture Decision Records (the ``kingmadoc adr`` command).

    Attributes:
        enabled: Allow ``kingmadoc adr`` to write ADRs.
        template: Bundled template name, or an explicit path relative to the project root.
    """

    enabled: bool = False
    template: str = "adr.md.j2"


@dataclass(frozen=True)
class FeatureDocConfig:
    """Complete KingmaDoc configuration."""

    output_dir: Path = Path("docs/features")
    template: str = "plan_default.md.j2"
    max_questions: int = 5
    project: ProjectConfig = field(default_factory=ProjectConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    diagrams: tuple[str, ...] = ("c4_context", "c4_container", "class", "sequence")
    diagram_format: str = "mermaid"
    diagrams_png: str = "embed"
    language: str = "en"
    extra_designs: ExtraDesignsConfig = field(default_factory=ExtraDesignsConfig)
    adr: AdrConfig = field(default_factory=AdrConfig)
    explain: ExplainConfig = field(default_factory=ExplainConfig)
    verify: VerifyConfig = field(default_factory=VerifyConfig)


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


# `kingmadoc plan --documents`: which of the functional (FO) and technical (TO) design
# documents are written next to the plan.
PLAN_DOCUMENTS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "single": (),
    "split": ("functional_design", "technical_design"),
    "functional": ("functional_design",),
    "technical": ("technical_design",),
})


def select_documents(config: FeatureDocConfig, documents: str) -> FeatureDocConfig:
    """Switch the FO and TO on or off, e.g. from ``kingmadoc plan --documents split``.

    ``single`` writes only the plan; ``split`` adds the functional and technical design;
    ``functional`` / ``technical`` add just that one. Other extra designs keep their
    configuration.

    Raises:
        ConfigError: If ``documents`` is not a key of :data:`PLAN_DOCUMENTS`.
    """
    if documents not in PLAN_DOCUMENTS:
        raise ConfigError(
            f"Unknown documents {documents!r}; supported: {', '.join(PLAN_DOCUMENTS)}"
        )
    chosen = PLAN_DOCUMENTS[documents]
    designs = {
        name: replace(getattr(config.extra_designs, name), enabled=name in chosen)
        if name in ("functional_design", "technical_design")
        else getattr(config.extra_designs, name)
        for name in DOCUMENT_MODELS
    }
    return replace(config, extra_designs=ExtraDesignsConfig(**designs))


def select_models(config: FeatureDocConfig, names: tuple[str, ...]) -> FeatureDocConfig:
    """Keep only the named design models, e.g. from ``kingmadoc plan --models``.

    Every extra design that has one of the models is switched on with just those
    models; every other extra design is switched off.

    Args:
        config: The loaded configuration.
        names: Model names from :data:`DOCUMENT_MODELS`.

    Returns:
        A new configuration.

    Raises:
        ConfigError: If a name is not a model of any document.
    """
    known = {m for models in DOCUMENT_MODELS.values() for m in models}
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ConfigError(f"Unknown model {unknown[0]!r}; supported: {', '.join(sorted(known))}")
    designs = {}
    for name, models in DOCUMENT_MODELS.items():
        chosen = tuple(m for m in models if m in names)
        designs[name] = replace(
            getattr(config.extra_designs, name), enabled=bool(chosen), models=chosen
        )
    return replace(config, extra_designs=ExtraDesignsConfig(**designs))


def resolve_output_dir(root: Path, config: FeatureDocConfig) -> Path:
    """Return ``output_dir`` as an absolute path, refusing anything outside ``root``.

    A repository's own ``.featuredoc.yml`` must not make KingmaDoc write elsewhere
    (``../..``, absolute paths, or symlinks pointing out of the project). Symlinks are
    resolved before the check.

    Args:
        root: Project root.
        config: KingmaDoc configuration.

    Returns:
        The resolved output directory (it may not exist yet).

    Raises:
        ConfigError: If ``output_dir`` resolves outside the project root.
    """
    project = root.resolve()
    target = (project / config.output_dir).resolve()
    if not target.is_relative_to(project):
        raise ConfigError(
            f"output_dir {config.output_dir.as_posix()!r} resolves to {target}, which is "
            f"outside the project root {project}"
        )
    return target


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
            "diagrams_png",
            "language",
            "extra_designs",
            "adr",
            "explain",
            "verify",
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

    diagrams_png = _get(data, "diagrams_png", str, defaults.diagrams_png)
    if diagrams_png not in DIAGRAMS_PNG_MODES:
        raise ConfigError(
            f"Unknown diagrams_png {diagrams_png!r}; supported: {', '.join(DIAGRAMS_PNG_MODES)}"
        )

    return FeatureDocConfig(
        output_dir=Path(_get(data, "output_dir", str, str(defaults.output_dir))),
        template=_get(data, "template", str, defaults.template),
        max_questions=max_questions,
        project=_parse_project(data.get("project")),
        analyzer=_parse_analyzer(data.get("analyzer")),
        diagrams=diagrams,
        diagram_format=diagram_format,
        diagrams_png=diagrams_png,
        language=_get(data, "language", str, defaults.language),
        extra_designs=_parse_extra_designs(data.get("extra_designs")),
        adr=_parse_adr(data.get("adr")),
        explain=_parse_explain(data.get("explain")),
        verify=_parse_verify(data.get("verify")),
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
  # Lines read per source file when scanning imports (imports sit at the top).
  max_lines_per_file: 2000
  exclude_dirs:
{excludes}

# Diagrams included in the plan doc.
diagrams:
  - c4_context
  - c4_container
  - class
  - sequence

# Diagram language: mermaid, plantuml (C4-PlantUML) or d2.
diagram_format: mermaid

# PNG below each Mermaid block (skill): embed (data URI), file (img/) or off.
diagrams_png: embed

# Language of fixed sentences, notes and captions; headings stay English.
language: en

# Optional extra documents written by `plan` next to the plan doc. `template` is a
# bundled name or an explicit path (e.g. ./my_design.md.j2); templates run sandboxed.
# `models` selects the design models (sections) of a document; default: all of them.
extra_designs:
  functional_design:
    # <slug>-functional-design.md, for stakeholders: user stories, use case diagram, per
    # story a use case, screen design (screenshot or wireframe) and evil user stories;
    # user flows.
    enabled: false
    template: functional_design.md.j2
    models: [{", ".join(DOCUMENT_MODELS["functional_design"])}]
  technical_design:
    # <slug>-technical-design.md, for developers: database schema, API contracts,
    # business rules, permissions, edge cases, error handling, performance and security,
    # threat model (Microsoft Threat Modeling Tool style), dependency graph.
    enabled: false
    template: technical_design.md.j2
    models: [{", ".join(DOCUMENT_MODELS["technical_design"])}]
  domain_design:
    # <slug>-domain-design.md: domain model and event storming.
    enabled: false
    template: domain_design.md.j2
    models: [{", ".join(DOCUMENT_MODELS["domain_design"])}]
  security_design:
    # <slug>-security-design.md: threat model (Threat Modeling Tool style) and who may
    # do what.
    enabled: false
    template: security_design.md.j2
    models: [{", ".join(DOCUMENT_MODELS["security_design"])}]

# Architecture Decision Records: `kingmadoc adr "<title>"` writes docs/adr/<NNNN>-<slug>.md.
adr:
  enabled: false
  template: adr.md.j2

# Explainers written by the explaining-code agent skill ("explain this project").
# format: arc42 (the 12 arc42 sections, default) or c4 (compact zoom-in).
# documents: single (one explainer, default), split (functional + technical, "FO/TO"),
# functional (only the FO) or technical (only the TO). The request overrides it.
# models: what the agent may draw (default: all; each only when the code has it). The
# request can narrow it too ("without screens", "only the threat model").
explain:
  format: arc42
  documents: single
  models: [{", ".join(EXPLAIN_MODELS)}]

# Verification (`kingmadoc verify`). Build, test and lint commands; null means detected
# from the project files. They only run with `kingmadoc verify --run-checks`.
verify:
  build: null
  test: null
  lint: null
  timeout: 600  # seconds per command
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
    _reject_unknown(
        data, {"exclude_dirs", "max_files", "tree_depth", "max_lines_per_file"}, "analyzer"
    )
    max_files = _get(data, "max_files", int, defaults.max_files, "analyzer.")
    tree_depth = _get(data, "tree_depth", int, defaults.tree_depth, "analyzer.")
    if not 1 <= max_files <= MAX_FILES_LIMIT:
        raise ConfigError(f"analyzer.max_files must be between 1 and {MAX_FILES_LIMIT}")
    if tree_depth < 1:
        raise ConfigError("analyzer.tree_depth must be >= 1")
    max_lines = _get(
        data, "max_lines_per_file", int, defaults.max_lines_per_file, "analyzer."
    )
    if max_lines < 1:
        raise ConfigError("analyzer.max_lines_per_file must be >= 1")
    return AnalyzerConfig(
        exclude_dirs=tuple(
            _get_str_list(data, "exclude_dirs", defaults.exclude_dirs, "analyzer.")
        ),
        max_files=max_files,
        tree_depth=tree_depth,
        max_lines_per_file=max_lines,
    )


def _parse_extra_designs(data: Any) -> ExtraDesignsConfig:
    if data is None:
        return ExtraDesignsConfig()
    data = _require_mapping(data, "extra_designs")
    defaults = ExtraDesignsConfig()
    names = {f.name for f in fields(ExtraDesignsConfig)}
    _reject_unknown(data, names, "extra_designs")
    designs: dict[str, ExtraDesignConfig] = {}
    for name in names & set(data):
        where = f"extra_designs.{name}"
        default: ExtraDesignConfig = getattr(defaults, name)
        entry = _require_mapping({} if data[name] is None else data[name], where)
        _reject_unknown(entry, {"enabled", "template", "models"}, where)
        models = tuple(_get_str_list(entry, "models", default.models, f"{where}."))
        unknown = [m for m in models if m not in DOCUMENT_MODELS[name]]
        if unknown:
            supported = ", ".join(DOCUMENT_MODELS[name]) or "none yet"
            raise ConfigError(
                f"Unknown model {unknown[0]!r} in {where}.models; supported: {supported}"
            )
        designs[name] = ExtraDesignConfig(
            enabled=_get(entry, "enabled", bool, default.enabled, f"{where}."),
            template=_get(entry, "template", str, default.template, f"{where}."),
            models=models,
        )
    return ExtraDesignsConfig(**designs)


def _parse_explain(data: Any) -> ExplainConfig:
    defaults = ExplainConfig()
    if data is None:
        return defaults
    data = _require_mapping(data, "explain")
    _reject_unknown(data, {"format", "documents", "models"}, "explain")
    fmt = _get(data, "format", str, defaults.format, "explain.")
    if fmt not in EXPLAIN_FORMATS:
        raise ConfigError(
            f"Unknown explain.format {fmt!r}; supported: {', '.join(EXPLAIN_FORMATS)}"
        )
    documents = _get(data, "documents", str, defaults.documents, "explain.")
    if documents not in EXPLAIN_DOCUMENTS:
        raise ConfigError(
            f"Unknown explain.documents {documents!r}; supported: {', '.join(EXPLAIN_DOCUMENTS)}"
        )
    models = tuple(_get_str_list(data, "models", defaults.models, "explain."))
    unknown = [m for m in models if m not in EXPLAIN_MODELS]
    if unknown:
        raise ConfigError(
            f"Unknown model {unknown[0]!r} in explain.models; supported: "
            f"{', '.join(EXPLAIN_MODELS)}"
        )
    return ExplainConfig(format=fmt, documents=documents, models=models)


def _parse_verify(data: Any) -> VerifyConfig:
    defaults = VerifyConfig()
    if data is None:
        return defaults
    data = _require_mapping(data, "verify")
    _reject_unknown(data, {"build", "test", "lint", "timeout"}, "verify")
    commands: dict[str, str | None] = {}
    for key in ("build", "test", "lint"):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ConfigError(f"verify.{key} must be a command (a non-empty string) or null")
        commands[key] = value
    timeout = _get(data, "timeout", int, defaults.timeout, "verify.")
    if timeout < 1:
        raise ConfigError("verify.timeout must be at least 1 (seconds)")
    return VerifyConfig(**commands, timeout=timeout)


def _parse_adr(data: Any) -> AdrConfig:
    defaults = AdrConfig()
    if data is None:
        return defaults
    data = _require_mapping(data, "adr")
    _reject_unknown(data, {"enabled", "template"}, "adr")
    return AdrConfig(
        enabled=_get(data, "enabled", bool, defaults.enabled, "adr."),
        template=_get(data, "template", str, defaults.template, "adr."),
    )


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
