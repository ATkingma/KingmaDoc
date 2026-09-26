"""Builds the plan context and renders the plan doc (Feature Design Doc)."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path

from jinja2 import TemplateError

from kingmadoc import __version__
from kingmadoc.config import ExtraDesignsConfig, FeatureDocConfig, resolve_output_dir
from kingmadoc.diagrams import get_backend
from kingmadoc.exceptions import GenerationError
from kingmadoc.naming import slugify
from kingmadoc.plan.analyzer import EXTENSION_LANGUAGES, SOURCE_LANGUAGES, CodebaseReport
from kingmadoc.templating import load_template

# More containers than this makes the inferred diagram unreadable.
MAX_INFERRED_CONTAINERS = 6
# The person drawn in the C4 diagrams.
USER_NAME = "User"
# The summary is the doc title; longer titles wrap badly in editors and PR views.
MAX_SUMMARY_LENGTH = 120
# Words ending in "." that do not end a sentence (compared lowercased, with the dot).
ABBREVIATIONS: frozenset[str] = frozenset({"e.g.", "i.e.", "etc.", "vs.", "cf.", "approx."})

PLAN_SUFFIX = "-plan.md"

# Detected technologies that count as data stores in the technical design doc.
DATA_STORES = frozenset({
    "PostgreSQL", "MySQL", "MariaDB", "MongoDB", "Redis", "Elasticsearch", "SQLite",
})

BASE_QUESTIONS: tuple[str, ...] = (
    "What problem does this feature solve, and for whom?",
    "Who or what triggers it (end user, scheduled job, external system, ...)?",
    "Which external systems, services, or data stores does it interact with?",
    "Which existing modules will change?{hint}",
    "How will you know it works? List the acceptance criteria.",
)


@dataclass(frozen=True)
class ExtraDesign:
    """An optional design doc that ``plan`` can write next to the plan doc.

    Its template (and whether it is enabled) comes from the field of the same name on
    :class:`~kingmadoc.config.ExtraDesignsConfig`.

    Attributes:
        name: Key under ``extra_designs`` in ``.featuredoc.yml``.
        suffix: File name suffix after the slug.
    """

    name: str
    suffix: str


# Order in which extra docs are written and printed: what (functional), then how (technical).
EXTRA_DESIGNS: tuple[ExtraDesign, ...] = (
    ExtraDesign("functional_design", "-functional-design.md"),
    ExtraDesign("technical_design", "-technical-design.md"),
)


def _check_extra_designs() -> None:
    """Fail at import time if EXTRA_DESIGNS and ExtraDesignsConfig disagree.

    Otherwise a mismatch would only surface as an AttributeError (or a silently
    ignored setting) when a user runs ``plan``.
    """
    registered = [d.name for d in EXTRA_DESIGNS]
    configured = [f.name for f in fields(ExtraDesignsConfig)]
    if sorted(registered) != sorted(configured):
        raise GenerationError(
            f"EXTRA_DESIGNS {registered} does not match the fields of "
            f"ExtraDesignsConfig {configured}"
        )


_check_extra_designs()


@dataclass(frozen=True)
class PlanContext:
    """Everything the plan template renders; built by :func:`build_plan_context`.

    Attributes:
        feature_description: The description as given on the command line.
        feature_summary: Its first sentence, at most ``MAX_SUMMARY_LENGTH`` characters.
        codebase_report: Result of analyzing the codebase.
        c4_context: Fenced C4 Context block ("" if disabled in the config).
        c4_container: Fenced C4 Container block ("" if disabled in the config).
        generated_at: When the doc was generated.
        version: KingmaDoc version that generated it.
        project_name: Project name (config, or the root directory name).
        answers: ``(question, answer)`` pairs; empty answers are still-open questions.
        diagram_format: ``diagram_format`` from the config (``mermaid``, ``plantuml``, ``d2``).
        diagram_label: Its display name for headings, e.g. ``"Mermaid"``.
    """

    feature_description: str
    feature_summary: str
    codebase_report: CodebaseReport
    c4_context: str
    c4_container: str
    generated_at: datetime
    version: str
    project_name: str
    answers: tuple[tuple[str, str], ...] = ()
    diagram_format: str = "mermaid"
    diagram_label: str = "Mermaid"


def build_questions(analysis: CodebaseReport, config: FeatureDocConfig) -> list[str]:
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


def build_plan_context(
    description: str,
    report: CodebaseReport,
    config: FeatureDocConfig,
    *,
    now: datetime,
    answers: Sequence[tuple[str, str]] = (),
) -> PlanContext:
    """Assemble the template context for a plan doc (pure: the caller passes the clock).

    Args:
        description: What the developer wants to build.
        report: Result of analyzing the codebase.
        config: KingmaDoc configuration.
        now: Generation timestamp.
        answers: ``(question, answer)`` pairs from the clarifying questions.

    Returns:
        A :class:`PlanContext`.

    Raises:
        GenerationError: If ``description`` is blank.
    """
    if not description.strip():
        raise GenerationError("The feature description must not be empty")
    project_name = config.project.name or report.root.name
    backend = get_backend(config.diagram_format)
    containers = infer_containers(report, project_name)
    # Diagram elements are referenced by name, so the actor must not share one.
    taken = {project_name, *(c["name"] for c in containers)}
    user = {
        "name": USER_NAME if USER_NAME not in taken else f"{USER_NAME} (person)",
        "description": "Person who uses the feature",
    }
    c4_context = c4_container = ""
    if "c4_context" in config.diagrams:
        c4_context = backend.render_context(
            project_name,
            external_actors=[user],
            external_systems=[],
            system_description=config.project.description,
        )
    if "c4_container" in config.diagrams:
        c4_container = backend.render_container(
            project_name,
            containers,
            relationships=[(user["name"], containers[0]["name"], "Uses")],
            external_actors=[user],
        )
    return PlanContext(
        feature_description=" ".join(description.split()),
        feature_summary=summarize(description),
        codebase_report=report,
        c4_context=c4_context,
        c4_container=c4_container,
        generated_at=now,
        version=__version__,
        project_name=project_name,
        answers=tuple(answers),
        diagram_format=config.diagram_format,
        diagram_label=backend.LABEL,
    )


def render_plan(context: PlanContext, config: FeatureDocConfig) -> str:
    """Render the plan doc as Markdown.

    Every :class:`PlanContext` field is a top-level template variable.

    Args:
        context: Result of :func:`build_plan_context`.
        config: KingmaDoc configuration (selects the template).

    Returns:
        The rendered Markdown document.

    Raises:
        ConfigError: If the configured template path does not exist or is not a file.
        GenerationError: If the template cannot be found or rendered.
    """
    variables = {f.name: getattr(context, f.name) for f in fields(context)}
    try:
        template = load_template(config.template, context.codebase_report.root)
        return template.render(**variables)
    except TemplateError as exc:
        raise GenerationError(f"Cannot render template {config.template!r}: {exc}") from exc


def enabled_extra_designs(config: FeatureDocConfig) -> tuple[ExtraDesign, ...]:
    """Return the extra design docs switched on under ``extra_designs`` in the config.

    Args:
        config: KingmaDoc configuration.

    Returns:
        Enabled entries of :data:`EXTRA_DESIGNS`, in that order.
    """
    return tuple(d for d in EXTRA_DESIGNS if getattr(config.extra_designs, d.name).enabled)


def render_extra_design(
    design: ExtraDesign, context: PlanContext, config: FeatureDocConfig, plan_path: Path
) -> str:
    """Render an optional design doc that accompanies a plan doc.

    Every :class:`PlanContext` field is a template variable, plus ``plan_file`` (the
    plan's file name, for a relative link) and ``data_stores`` (detected databases).

    Args:
        design: Which extra doc to render (from :data:`EXTRA_DESIGNS`).
        context: Result of :func:`build_plan_context`.
        config: KingmaDoc configuration (selects the template).
        plan_path: Where the plan doc is written.

    Returns:
        The rendered Markdown document.

    Raises:
        ConfigError: If the configured template path does not exist or is not a file.
        GenerationError: If the template cannot be found or rendered.
    """
    template_name = getattr(config.extra_designs, design.name).template
    variables = {f.name: getattr(context, f.name) for f in fields(context)}
    variables["plan_file"] = plan_path.name
    variables["data_stores"] = [
        tech for tech in context.codebase_report.detected_stack if tech in DATA_STORES
    ]
    try:
        template = load_template(template_name, context.codebase_report.root)
        return template.render(**variables)
    except TemplateError as exc:
        raise GenerationError(f"Cannot render template {template_name!r}: {exc}") from exc


def extra_design_path(design: ExtraDesign, plan_path: Path) -> Path:
    """Return the path of an extra design doc: next to the plan, same slug.

    Args:
        design: Which extra doc (from :data:`EXTRA_DESIGNS`).
        plan_path: ``.../<slug>-plan.md`` (or any custom ``--output`` path).

    Returns:
        ``.../<slug><design.suffix>`` in the same directory.

    Example:
        >>> plan = Path("docs/features/add-login-plan.md")
        >>> extra_design_path(EXTRA_DESIGNS[0], plan).as_posix()
        'docs/features/add-login-functional-design.md'
    """
    stem = plan_path.name.removesuffix(PLAN_SUFFIX)
    if stem == plan_path.name:
        stem = plan_path.stem
    return plan_path.with_name(stem + design.suffix)


def summarize(description: str, max_length: int = MAX_SUMMARY_LENGTH) -> str:
    """Return the first sentence of ``description``, shortened to ``max_length``.

    Args:
        description: Free text.
        max_length: Maximum length of the result, including a trailing ``…``.

    A sentence ends at ``.``, ``!`` or ``?`` followed by whitespace and a capital
    letter, unless the word before it is a known abbreviation (:data:`ABBREVIATIONS`).

    Returns:
        The first sentence with whitespace collapsed; cut at a word boundary if too long.

    Example:
        >>> summarize("Add export, e.g. CSV. Also add logout.")
        'Add export, e.g. CSV.'
    """
    text = " ".join(description.split())
    sentence = _first_sentence(text)
    if len(sentence) <= max_length:
        return sentence
    cut = sentence[: max_length - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def _first_sentence(text: str) -> str:
    for match in re.finditer(r"[.!?] (?=\S)", text):
        end = match.start() + 1
        if not text[match.end()].isupper():
            continue
        if text[:end].rsplit(" ", 1)[-1].lower() in ABBREVIATIONS:
            continue
        return text[:end]
    return text


def infer_containers(analysis: CodebaseReport, project_name: str) -> list[dict[str, str]]:
    """Guess C4 containers from detected source directories.

    This is a heuristic starting point; the generated doc asks the reader to review it.

    Args:
        analysis: Result of analyzing the codebase.
        project_name: Fallback label when no source directories are found.

    Returns:
        Container specs (``name``, ``tech``, ``description``) for
        :func:`kingmadoc.diagrams.c4.render_container`: one per source directory (capped),
        or a single project container.
    """
    technology = analysis.primary_language or "Unknown"
    if not analysis.source_dirs:
        return [{"name": project_name, "tech": technology, "description": "Main application"}]
    dirs = analysis.source_dirs[:MAX_INFERRED_CONTAINERS]
    # Same directory name in two places (app/ and src/app/): use the paths instead.
    counts = Counter(d.name for d in dirs)
    return [
        {
            "name": d.name if counts[d.name] == 1 else d.as_posix(),
            "tech": _dir_language(analysis, d) or technology,
            "description": f"Source module {d.as_posix()}/",
        }
        for d in dirs
    ]


def default_output_path(root: Path, config: FeatureDocConfig, description: str) -> Path:
    """Return where the plan doc for ``description`` is written by default.

    Args:
        root: Project root.
        config: KingmaDoc configuration.
        description: Feature description (the slug is derived from it).

    Returns:
        ``<root>/<output_dir>/<slug>-plan.md`` (resolved), see :func:`feature_slug`.

    Raises:
        ConfigError: If ``output_dir`` resolves outside the project root.
    """
    return resolve_output_dir(root, config) / f"{feature_slug(description)}{PLAN_SUFFIX}"


def feature_slug(description: str) -> str:
    """Derive the file slug for a feature from the first sentence of its description.

    Args:
        description: Feature description.

    Returns:
        Kebab-case slug of at most :data:`kingmadoc.naming.MAX_SLUG_LENGTH` characters.

    Example:
        >>> feature_slug("Add password reset via email. Links expire after 30 minutes.")
        'add-password-reset-via-email'
    """
    return slugify(summarize(description))


def _dir_language(analysis: CodebaseReport, directory: Path) -> str | None:
    counts = Counter(
        SOURCE_LANGUAGES[language]
        for f in analysis.files
        if (language := EXTENSION_LANGUAGES.get(f.suffix.lower())) in SOURCE_LANGUAGES
        and f.is_relative_to(directory)
    )
    return counts.most_common(1)[0][0] if counts else None
