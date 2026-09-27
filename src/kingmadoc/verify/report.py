"""The Feature Verification Doc (pure: the caller passes the clock and the findings)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from kingmadoc import __version__
from kingmadoc.verify.changes import Changes
from kingmadoc.verify.commands import KINDS, CheckCommand, CheckResult
from kingmadoc.verify.deviations import Deviation

VERIFY_STATUSES: tuple[str, ...] = ("Matches plan", "Deviations found", "Not verified")


def verify_status(
    changes: Changes, deviations: Sequence[Deviation], results: Sequence[CheckResult],
    plan_problem: str | None = None,
) -> str:
    """Return the verification status: one of :data:`VERIFY_STATUSES`.

    Args:
        changes: What changed since the plan.
        deviations: What differs from the plan.
        results: The checks (run or not).
        plan_problem: Why the plan could not be read (no frontmatter, ...).

    Returns:
        ``Not verified`` when the changes or the plan could not be read,
        ``Deviations found`` for a deviation or a failed check, else ``Matches plan``.
    """
    if changes.problem or plan_problem:
        return "Not verified"
    if deviations or any(r.passed is False for r in results):
        return "Deviations found"
    return "Matches plan"


def render_verify(
    slug: str,
    plan_ref: str,
    *,
    now: datetime,
    status: str,
    changes: Changes,
    deviations: Sequence[Deviation],
    commands: Sequence[CheckCommand],
    results: Sequence[CheckResult],
    plan_problem: str | None = None,
) -> str:
    """Render ``<slug>-verify.md`` (the same headings as the skill's verify format).

    Args:
        slug: Feature slug.
        plan_ref: The plan's path relative to the project root.
        now: Generation timestamp.
        status: From :func:`verify_status`.
        changes: What changed since the plan.
        deviations: What differs from the plan.
        commands: The detected check commands.
        results: The results of the commands that ran (empty without ``--run-checks``).
        plan_problem: Why the plan's frontmatter could not be read, if so.

    Returns:
        Markdown text.
    """
    plan_name = Path(plan_ref).name
    lines = [
        f"# Verification: {slug}",
        "",
        "| | |",
        "|---|---|",
        f"| **Plan** | [`{plan_ref}`]({plan_name}) |",
        f"| **Status** | {status} |",
        f"| **Generated** | {now.isoformat(timespec='minutes')} by KingmaDoc {__version__} |",
        "",
        f"> {_basis(changes, plan_problem)}",
        "> Review every deviation: KingmaDoc reports, it does not decide.",
        "",
        "## Deviations",
        "",
    ]
    if deviations:
        lines += ["| # | Area | Plan says | Code does | Impact |",
                  "| --- | --- | --- | --- | --- |"]
        lines += [f"| {n} | {d.area} | {_cell(d.plan)} | {_cell(d.code)} | {d.impact} |"
                  for n, d in enumerate(deviations, start=1)]
    elif status == "Not verified":
        lines.append("_Not verified: see the note above._")
    else:
        lines.append("_No deviations found._")
    lines += ["", "## Validation results", "", "| Check | Command | Result |",
              "| --- | --- | --- |"]
    by_kind = {c.kind: c for c in commands}
    ran = {r.kind: r for r in results}
    for kind in KINDS:
        command = by_kind.get(kind)
        result = ran.get(kind)
        shown = f"`{command.command}`" if command else "_none found_"
        if result is not None:
            outcome = "passed" if result.passed else _cell(result.detail)
        elif command is not None:
            outcome = "_not run_: run `kingmadoc verify --run-checks` to run it"
        else:
            outcome = "_not run_: set `verify` in `.featuredoc.yml`"
        lines.append(f"| {kind} | {shown} | {outcome} |")
    return "\n".join(lines) + "\n"


def _basis(changes: Changes, plan_problem: str | None) -> str:
    if plan_problem:
        return (f"Not verified: {plan_problem}. Run `kingmadoc check` and fix the plan's "
                "frontmatter.")
    if changes.problem:
        return f"Not verified: {changes.problem}."
    since = f"commit {changes.base}" if changes.base else "the first commit"
    count = len(changes.files)
    return (f"Verified by `kingmadoc verify` against {since} plus uncommitted changes: "
            f"{count} file{'s' if count != 1 else ''} changed since the plan.")


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")
