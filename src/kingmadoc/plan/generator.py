"""Renders the Feature Design Doc from analysis results and user answers."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from importlib.resources import files as package_files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

from kingmadoc import __version__
from kingmadoc.config import FeatureDocConfig
from kingmadoc.diagrams.c4 import (
    Container,
    Person,
    Relationship,
    build_container_diagram,
    build_context_diagram,
    make_alias,
)
from kingmadoc.exceptions import GenerationError
from kingmadoc.plan.analyzer import EXTENSION_LANGUAGES, AnalysisResult

MAX_INFERRED_CONTAINERS = 6

BASE_QUESTIONS: tuple[str, ...] = (
    "What problem does this feature solve, and for whom?",
    "Who or what triggers it (end user, scheduled job, external system, ...)?",
    "Which external systems, services, or data stores does it interact with?",
    "Which existing modules will change?{hint}",
    "How will you know it works? List the acceptance criteria.",
)


@dataclass(frozen=True)
class FeatureRequest:
    """What the developer wants to build, plus their answers to clarifying questions."""

    name: str
    description: str = ""
    answers: list[tuple[str, str]] = field(default_factory=list)


def build_questions(analysis: AnalysisResult, config: FeatureDocConfig) -> list[str]:
    """Return up to ``config.max_questions`` clarifying questions for this codebase.

    Args:
        analysis: Result of analyzing the codebase.
        config: KingmaDoc configuration.

    Returns:
        Question strings, in the order they should be asked.
    """
    dirs = ", ".join(f"`{d.as_posix()}`" for d in analysis.source_dirs[:5])
    hint = f" (detected modules: {dirs})" if dirs else ""
    questions = [q.format(hint=hint) for q in BASE_QUESTIONS]
    return questions[: config.max_questions]


def render_plan(
    feature: FeatureRequest, analysis: AnalysisResult, config: FeatureDocConfig
) -> str:
    """Render the Feature Design Doc as Markdown.

    Args:
        feature: The feature request and answers.
        analysis: Result of analyzing the codebase.
        config: KingmaDoc configuration.

    Returns:
        The rendered Markdown document.

    Raises:
        GenerationError: If the template cannot be found or rendered.
    """
    project_name = config.project.name or analysis.root.name
    system_alias = make_alias(project_name)
    user = Person("user", "User", "Person who uses the feature")
    containers = infer_containers(analysis, project_name)

    diagrams: dict[str, str] = {}
    if "c4_context" in config.diagrams:
        diagrams["c4_context"] = build_context_diagram(
            system_alias=system_alias,
            system_label=project_name,
            system_description=config.project.description or feature.description,
            people=[user],
            external_systems=[],
            relationships=[Relationship(user.alias, system_alias, f"Uses {feature.name}")],
        )
    if "c4_container" in config.diagrams:
        diagrams["c4_container"] = build_container_diagram(
            system_alias=system_alias,
            system_label=project_name,
            people=[user],
            containers=containers,
            external_systems=[],
            relationships=(
                [Relationship(user.alias, containers[0].alias, "Uses")] if containers else []
            ),
        )

    env = _environment(analysis.root)
    try:
        template = env.get_template(config.template)
        return template.render(
            feature=feature,
            project_name=project_name,
            project_description=config.project.description,
            analysis=analysis,
            diagrams=diagrams,
            generated_on=date.today().isoformat(),
            version=__version__,
        )
    except TemplateError as exc:
        raise GenerationError(f"Cannot render template {config.template!r}: {exc}") from exc


def infer_containers(analysis: AnalysisResult, project_name: str) -> list[Container]:
    """Guess C4 containers from detected source directories.

    This is a heuristic starting point; the generated doc asks the reader to review it.

    Args:
        analysis: Result of analyzing the codebase.
        project_name: Fallback label when no source directories are found.

    Returns:
        One container per source directory (capped), or a single project container.
    """
    technology = analysis.primary_language or "Unknown"
    if not analysis.source_dirs:
        return [Container("app", project_name, technology, "Main application")]
    return [
        Container(
            alias=make_alias(d.as_posix()),
            label=d.name,
            technology=_dir_language(analysis, d) or technology,
            description=f"Source module {d.as_posix()}/",
        )
        for d in analysis.source_dirs[:MAX_INFERRED_CONTAINERS]
    ]


def default_output_path(root: Path, config: FeatureDocConfig, feature_name: str) -> Path:
    """Return where the plan doc for ``feature_name`` is written by default.

    Args:
        root: Project root.
        config: KingmaDoc configuration.
        feature_name: Human-readable feature name.

    Returns:
        ``<root>/<output_dir>/<slug>/design.md``.
    """
    return root / config.output_dir / slugify(feature_name) / "design.md"


def write_document(content: str, path: Path, overwrite: bool = False) -> Path:
    """Write ``content`` to ``path``, creating parent directories.

    Args:
        content: Document text.
        path: Destination file.
        overwrite: Replace an existing file if True.

    Returns:
        The written path.

    Raises:
        GenerationError: If the file exists (and ``overwrite`` is False) or cannot be written.
    """
    if path.exists() and not overwrite:
        raise GenerationError(f"{path} already exists (use --force to overwrite)")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise GenerationError(f"Cannot write {path}: {exc}") from exc
    return path


def slugify(text: str) -> str:
    """Convert text to a filesystem-friendly slug.

    Args:
        text: Any string.

    Returns:
        Lowercase, hyphen-separated slug (``"feature"`` if nothing remains).
    """
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "feature"


def template_dirs(root: Path) -> list[Path]:
    """Template search path: project root, bundled templates, repo checkout.

    Args:
        root: Project root (for project-local templates referenced by relative path).

    Returns:
        Existing directories, highest priority first.
    """
    candidates = [
        root,
        Path(str(package_files("kingmadoc") / "templates")),  # installed wheel
        Path(__file__).resolve().parents[3] / "templates",  # editable/source checkout
    ]
    return [d for d in candidates if d.is_dir()]


def _environment(root: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader([str(d) for d in template_dirs(root)]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,  # Markdown output, not HTML.
    )


def _dir_language(analysis: AnalysisResult, directory: Path) -> str | None:
    counts = Counter(
        EXTENSION_LANGUAGES[f.suffix]
        for f in analysis.files
        if f.suffix in EXTENSION_LANGUAGES and f.is_relative_to(directory)
    )
    return counts.most_common(1)[0][0] if counts else None
