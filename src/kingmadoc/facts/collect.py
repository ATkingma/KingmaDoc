"""Collect the facts about a project and write them as Markdown or JSON."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kingmadoc.facts.branch import BranchChanges
from kingmadoc.facts.data_model import Entity, data_model
from kingmadoc.facts.projects import PROJECT_SUFFIXES, Edge, project_references
from kingmadoc.plan.analyzer import TEST_DIR_NAMES, CodebaseReport

# Files the data-model parsers read, and the size above which a file is skipped
# (generated code, fixtures).
MODEL_SUFFIXES = (".cs", ".prisma", ".py", ".ts")
MAX_FILE_BYTES = 512_000
# Longest list of changed files and dependencies shown in Markdown (JSON has them all).
MAX_LISTED = 60


@dataclass(frozen=True)
class Facts:
    """Everything ``kingmadoc explain facts`` reports about one project."""

    project: str
    commit: str | None
    report: CodebaseReport
    project_references: tuple[Edge, ...]
    entities: tuple[Entity, ...]
    branch: BranchChanges | None


def collect_facts(
    report: CodebaseReport, commit: str | None, branch: BranchChanges | None
) -> Facts:
    """Read the project references and the data model from the analyzed files.

    Args:
        report: The analysis (with module dependencies) of the project.
        commit: The commit the facts describe (HEAD), if known.
        branch: What the branch changed, when a base was given.

    Returns:
        The facts.
    """
    manifests: dict[str, str] = {}
    sources: dict[str, str] = {}
    for relative in report.files:
        if relative.suffix in PROJECT_SUFFIXES:
            manifests[relative.as_posix()] = _read(report.root / relative)
        elif relative.suffix in MODEL_SUFFIXES and not _is_test(relative):
            sources[relative.as_posix()] = _read(report.root / relative)
    return Facts(
        project=report.root.resolve().name,
        commit=commit,
        report=report,
        project_references=project_references(manifests),
        entities=data_model(sources),
        branch=branch,
    )


def facts_markdown(facts: Facts) -> str:
    """Write the facts as Markdown, for an agent (or a person) to draw from.

    Args:
        facts: From :func:`collect_facts`.

    Returns:
        The Markdown text.
    """
    report = facts.report
    at = f" at commit {facts.commit}" if facts.commit else ""
    lines = [
        f"# Facts: {facts.project}",
        "",
        f"Read from the code{at} by `kingmadoc explain facts`. Draw from these facts; do not",
        "contradict them. Everything else still comes from reading the code.",
        "",
        "## Project",
        "",
        f"- Stack: {', '.join(report.detected_stack) or 'not detected'}",
        f"- Entry points: {_codes(report.entry_points) or 'none found'}",
        f"- Source folders: {_codes(p.as_posix() for p in report.source_dirs) or 'none found'}",
        f"- Tests: {_codes(report.test_dirs) or 'none found'}",
        "",
        "## Project references",
        "",
    ]
    lines += _edges(facts.project_references, "no .NET project references")
    lines += ["", "## Python module dependencies", ""]
    lines += _edges(report.module_dependencies or (), "none (or no Python)")
    lines += ["", "## Data model"]
    if not facts.entities:
        lines += ["", "_none found (EF Core, Prisma, Django, SQLAlchemy, TypeORM)._"]
    for entity in facts.entities:
        lines += ["", f"### {entity.name} ({entity.orm}, `{entity.source}`)", ""]
        lines += [f"- {f.name}: {f.type}" for f in entity.fields]
        lines += [f"- {r.name} → {r.target} ({r.kind})" for r in entity.relations]
    if facts.branch:
        lines += ["", *_branch(facts.branch)]
    return "\n".join(lines) + "\n"


def facts_to_dict(facts: Facts) -> dict[str, Any]:
    """Return the facts as JSON-serializable data (``--json``).

    Args:
        facts: From :func:`collect_facts`.

    Returns:
        A dict with plain lists, strings and numbers.
    """
    report = facts.report
    branch = facts.branch
    return {
        "project": facts.project,
        "commit": facts.commit,
        "stack": list(report.detected_stack),
        "entry_points": list(report.entry_points),
        "source_dirs": [p.as_posix() for p in report.source_dirs],
        "test_dirs": list(report.test_dirs),
        "project_references": [list(e) for e in facts.project_references],
        "module_dependencies": [list(e) for e in report.module_dependencies or ()],
        "data_model": [asdict(e) for e in facts.entities],
        "branch": None if branch is None else {
            "base": branch.base,
            "head": branch.head,
            "merge_base": branch.merge_base,
            "commits": [{"commit": c, "subject": s} for c, s in branch.commits],
            "files": [asdict(f) for f in branch.files],
        },
    }


def _branch(branch: BranchChanges) -> list[str]:
    lines = [
        f"## Branch {branch.head} (compared with {branch.base})",
        "",
        f"Since the merge base {branch.merge_base}, including uncommitted changes.",
        "",
        f"Commits ({len(branch.commits)}):",
        "",
        *[f"- {sha} {subject}" for sha, subject in branch.commits],
        "",
        f"Files changed ({len(branch.files)}):",
        "",
        "| Status | File | Added | Removed |",
        "| --- | --- | --- | --- |",
    ]
    for f in branch.files[:MAX_LISTED]:
        added = "binary" if f.added is None else f"+{f.added}"
        removed = "" if f.removed is None else f"−{f.removed}"
        lines.append(f"| {f.status} | `{f.path}` | {added} | {removed} |")
    if len(branch.files) > MAX_LISTED:
        lines.append(f"| | … {len(branch.files) - MAX_LISTED} more (see --json) | | |")
    return lines


def _edges(edges: tuple[Edge, ...], empty: str) -> list[str]:
    if not edges:
        return [f"_{empty}._"]
    lines = [f"- {a} → {b}" for a, b in edges[:MAX_LISTED]]
    if len(edges) > MAX_LISTED:
        lines.append(f"- … {len(edges) - MAX_LISTED} more (see --json)")
    return lines


def _codes(items: Any) -> str:
    return ", ".join(f"`{item}`" for item in items)


def _is_test(path: Path) -> bool:
    """Tests and their fixtures are not the project's own model."""
    name = path.name
    return (
        any(part in TEST_DIR_NAMES for part in path.parts[:-1])
        or name.startswith("test_")
        or name.endswith(("_test.py", ".spec.ts", ".test.ts", "Tests.cs", "Test.cs"))
    )


def _read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return ""
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
