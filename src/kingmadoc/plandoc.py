"""Machine-readable plan docs: the YAML frontmatter and the REQ-n requirements (WP1).

A plan starts with a frontmatter block (convention B2) that tools read instead of the
Markdown text::

    ---
    kingmadoc: 1                 # format version
    feature: "password-reset"    # the slug, as in <slug>-plan.md (quoted: "no", "2024")
    status: draft                # draft | approved | implemented | partial
    requirements: [REQ-1, REQ-2] # defined in the "Requirements" section
    files_expected: [src/auth/reset.py]
    ---

Pure functions only: the CLI reads and writes the files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

import yaml

from kingmadoc.exceptions import PlanFormatError

FORMAT_VERSION = 1
STATUSES: tuple[str, ...] = ("draft", "approved", "implemented", "partial")
KEYS: tuple[str, ...] = ("kingmadoc", "feature", "status", "requirements", "files_expected")
REQUIREMENT_ID = re.compile(r"REQ-[1-9]\d*")
_DEFINED = re.compile(r"^\s*[-*]\s+\*\*(REQ-[1-9]\d*)\*\*\s*:", re.M)
_FRONTMATTER = re.compile(r"\A---\n(.*?)^---\n", re.S | re.M)
_GENERATED_ROW = re.compile(r"^\|\s*\*\*Generated\*\*\s*\|\s*(\S+)", re.M)
_STATUS_ROW = re.compile(r"^(\|\s*\*\*Status\*\*\s*\|\s*)[^|\n]*?(\s*\|)$", re.M)


@dataclass(frozen=True)
class PlanMeta:
    """The frontmatter of a plan doc."""

    feature: str
    status: str
    requirements: tuple[str, ...]
    files_expected: tuple[str, ...]


def check_plan(text: str, slug: str | None = None) -> list[str]:
    """Return every problem with a plan doc's frontmatter and requirements.

    Args:
        text: The plan doc.
        slug: The slug from its file name, which ``feature`` must equal (None: skip).

    Returns:
        One message per problem; empty when the plan is valid.
    """
    match = _FRONTMATTER.match(text)
    if not match:
        return ["no frontmatter: the plan must start with a '---' YAML block (kingmadoc: 1, ...)"]
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return [f"the frontmatter is not valid YAML: {str(exc).splitlines()[0]}"]
    if not isinstance(data, dict):
        return ["the frontmatter must be a YAML mapping (key: value lines)"]

    problems = [f"unknown key {k!r} (known: {', '.join(KEYS)})" for k in data if k not in KEYS]
    problems += [f"missing key {k!r}" for k in KEYS if k not in data]
    if data.get("kingmadoc", FORMAT_VERSION) != FORMAT_VERSION:
        problems.append(
            f"format version kingmadoc: {data['kingmadoc']!r}; expected {FORMAT_VERSION}"
        )
    feature = data.get("feature")
    if "feature" in data and not isinstance(feature, str):
        problems.append(
            f"feature must be the slug as a string; quote it: feature: \"{feature}\""
        )
    elif slug is not None and feature is not None and feature != slug:
        problems.append(f"feature {feature!r} does not match the file name ({slug}-plan.md)")
    status = data.get("status")
    if "status" in data and status not in STATUSES:
        problems.append(f"status {status!r} is not one of {', '.join(STATUSES)}")
    problems += _check_requirements(data.get("requirements"), text[match.end():])
    problems += _check_files(data.get("files_expected"))
    return problems


def parse_plan(text: str) -> PlanMeta:
    """Read a plan doc's frontmatter.

    Args:
        text: The plan doc.

    Returns:
        The metadata.

    Raises:
        PlanFormatError: If :func:`check_plan` finds a problem (all are listed).
    """
    problems = check_plan(text)
    if problems:
        raise PlanFormatError("; ".join(problems))
    match = _FRONTMATTER.match(text)
    if match is None:  # unreachable: check_plan reports a missing frontmatter
        raise PlanFormatError("no frontmatter")
    data: dict[str, Any] = yaml.safe_load(match.group(1))
    return PlanMeta(
        feature=data["feature"],
        status=data["status"],
        requirements=tuple(data["requirements"] or ()),
        files_expected=tuple(data["files_expected"] or ()),
    )


def generated_at(text: str) -> datetime | None:
    """Return when the plan was generated (its **Generated** row), if it says.

    Args:
        text: The plan doc.

    Returns:
        The timestamp, or None when the row is missing or not an ISO date and time.
    """
    match = _GENERATED_ROW.search(text)
    try:
        return datetime.fromisoformat(match.group(1)) if match else None
    except ValueError:
        return None


def set_status(text: str, status: str) -> str:
    """Return the plan with a new status, in the frontmatter and in the header table.

    Args:
        text: A valid plan doc.
        status: One of :data:`STATUSES`.

    Returns:
        The changed text; everything else is kept byte for byte.

    Raises:
        PlanFormatError: If the status is unknown or the plan has no status line.
    """
    if status not in STATUSES:
        raise PlanFormatError(f"status {status!r} is not one of {', '.join(STATUSES)}")
    match = _FRONTMATTER.match(text)
    if not match or not re.search(r"^status:.*$", match.group(1), re.M):
        raise PlanFormatError("the plan has no 'status:' line in its frontmatter")
    front = re.sub(r"^status:.*$", f"status: {status}", match.group(1), count=1, flags=re.M)
    body = _STATUS_ROW.sub(lambda m: m.group(1) + status.capitalize() + m.group(2),
                           text[match.end():], count=1)
    return f"---\n{front}---\n{body}"


def _check_requirements(listed: Any, body: str) -> list[str]:
    if not isinstance(listed, list):
        return ["requirements must be a list, e.g. [REQ-1, REQ-2]"]
    problems = [f"{r!r} is not a requirement ID (REQ-1, REQ-2, ...)"
                for r in listed if not (isinstance(r, str) and REQUIREMENT_ID.fullmatch(r))]
    problems += [f"{r} is listed twice" for r in sorted({r for r in listed if listed.count(r) > 1},
                                                          key=str)]
    defined = _DEFINED.findall(body)
    problems += [f"{r} is listed in the frontmatter but not defined as '- **{r}**: ...'"
                 for r in listed if isinstance(r, str) and REQUIREMENT_ID.fullmatch(r)
                 and r not in defined]
    problems += [f"{r} is defined in the text but missing from 'requirements'"
                 for r in dict.fromkeys(defined) if r not in listed]
    return problems


def _check_files(files: Any) -> list[str]:
    if not isinstance(files, list):
        return ["files_expected must be a list of paths (may be empty: [])"]
    problems = []
    for path in files:
        if not isinstance(path, str) or not path.strip():
            problems.append(f"files_expected: {path!r} is not a path")
        elif path.startswith("/") or ".." in PurePosixPath(path).parts or "\\" in path:
            problems.append(f"files_expected: {path} must be relative to the project root")
    return problems
