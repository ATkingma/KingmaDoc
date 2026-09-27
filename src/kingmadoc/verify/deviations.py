"""Where the code differs from its plan (pure: the CLI collects the inputs)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from kingmadoc.plandoc import PlanMeta
from kingmadoc.verify.changes import Changes

# How many changed files outside the plan are named in one deviation.
MAX_LISTED = 10
_MERMAID_CONTAINER = re.compile(r"\bContainer(?:Db|Queue)?\(\s*\w+\s*,\s*\"([^\"]+)\"")
_D2_CONTAINER = re.compile(r"^\s+\w+: \"([^\"\\\n]+)\\n\[", re.M)


@dataclass(frozen=True)
class Deviation:
    """One difference between the plan and the code."""

    area: str
    plan: str
    code: str
    impact: str


def planned_containers(plan_text: str) -> tuple[str, ...]:
    """Return the container names in the plan's C4 container diagram (any backend).

    Args:
        plan_text: The plan doc.

    Returns:
        The names, in order of appearance, without duplicates.
    """
    names = _MERMAID_CONTAINER.findall(plan_text) + _D2_CONTAINER.findall(plan_text)
    return tuple(dict.fromkeys(names))


def mentioned_requirements(texts: list[str]) -> frozenset[str]:
    """Return the requirement IDs mentioned anywhere in ``texts`` (tests, commit messages).

    Args:
        texts: File contents and commit messages.

    Returns:
        E.g. ``frozenset({"REQ-1"})``.
    """
    return frozenset(m for text in texts for m in re.findall(r"\bREQ-[1-9]\d*\b", text))


def find_deviations(
    meta: PlanMeta | None,
    changes: Changes,
    mentioned: frozenset[str],
    planned: tuple[str, ...],
    current: tuple[str, ...],
) -> tuple[Deviation, ...]:
    """Compare the plan with what changed.

    Args:
        meta: The plan's frontmatter (None: the plan has none).
        changes: What changed since the plan.
        mentioned: Requirement IDs that a test file or a commit message mentions.
        planned: Container names in the plan's diagram.
        current: Container names inferred from the code now.

    Returns:
        The deviations: process, scope, requirements, architecture.
    """
    found: list[Deviation] = []
    if meta is not None and meta.status == "draft" and changes.files:
        found.append(Deviation(
            "Process", "no code before `kingmadoc approve`", "the plan is still draft", "High"
        ))
    if meta is not None:
        found += _scope(meta.files_expected, changes.files)
        found += [
            Deviation("Requirement", f"{req} is met", f"no test or commit mentions {req}",
                      "Medium")
            for req in meta.requirements if req not in mentioned
        ]
    if planned:
        found += [
            Deviation("Architecture", "not in the plan's container diagram",
                      f"container `{name}` exists", "Medium")
            for name in current if name not in planned
        ]
        found += [
            Deviation("Architecture", f"container `{name}`", "no longer found in the code", "Low")
            for name in planned if name not in current
        ]
    return tuple(found)


def _scope(expected: tuple[str, ...], changed: tuple[str, ...]) -> list[Deviation]:
    if not expected:
        return []

    def under(path: str, prefix: str) -> bool:
        return path == prefix or path.startswith(prefix.rstrip("/") + "/")

    found = [
        Deviation("Scope", f"`{path}` changes", "not changed", "Medium")
        for path in expected if not any(under(c, path) for c in changed)
    ]
    outside = [c for c in changed if not any(under(c, path) for path in expected)]
    if outside:
        shown = ", ".join(f"`{p}`" for p in outside[:MAX_LISTED])
        more = f" and {len(outside) - MAX_LISTED} more" if len(outside) > MAX_LISTED else ""
        found.append(Deviation(
            "Scope", "only the files in `files_expected` change", f"also changed: {shown}{more}",
            "Low",
        ))
    return found
