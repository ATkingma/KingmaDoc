"""Phase 1 verify stub: finds the plan doc and writes a placeholder verification doc."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from kingmadoc import __version__
from kingmadoc.config import FeatureDocConfig
from kingmadoc.exceptions import VerificationError

PLAN_SUFFIX = "-plan.md"
VERIFY_SUFFIX = "-verify.md"

# Same shape `plan` produces; also keeps slugs from escaping output_dir ("../x").
SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def find_plan(root: Path, config: FeatureDocConfig, slug: str) -> Path:
    """Return the plan doc for ``slug``.

    Args:
        root: Project root.
        config: KingmaDoc configuration (``output_dir``).
        slug: Feature slug, as in ``<slug>-plan.md``.

    Returns:
        Path of the existing ``<root>/<output_dir>/<slug>-plan.md``.

    Raises:
        VerificationError: If the slug is malformed or the plan doc does not exist.
    """
    if not SLUG_PATTERN.fullmatch(slug):
        raise VerificationError(
            f"Invalid feature slug {slug!r}: use lowercase letters, digits and hyphens "
            f"(the part before {PLAN_SUFFIX!r})"
        )
    plan_dir = root / config.output_dir
    path = plan_dir / f"{slug}{PLAN_SUFFIX}"
    if path.is_file():
        return path
    available = sorted(p.name.removesuffix(PLAN_SUFFIX) for p in plan_dir.glob(f"*{PLAN_SUFFIX}"))
    hint = (
        f"Available: {', '.join(available)}"
        if available
        else 'Run `kingmadoc plan "<description>"` first'
    )
    raise VerificationError(f"No plan doc found at {path}. {hint}.")


def verify_output_path(plan_path: Path) -> Path:
    """Return where the verification doc for ``plan_path`` goes (next to the plan).

    Args:
        plan_path: ``.../<slug>-plan.md``.

    Returns:
        ``.../<slug>-verify.md``.
    """
    return plan_path.with_name(plan_path.name.removesuffix(PLAN_SUFFIX) + VERIFY_SUFFIX)


def render_verify_stub(slug: str, plan_ref: str, *, now: datetime) -> str:
    """Render the placeholder verification doc (pure: the caller passes the clock).

    Args:
        slug: Feature slug.
        plan_ref: Plan doc path as shown to the reader (relative to the project root).
        now: Generation timestamp.

    Returns:
        Markdown text.
    """
    plan_name = Path(plan_ref).name
    return f"""# Verification: {slug}

| | |
|---|---|
| **Plan** | [`{plan_ref}`]({plan_name}) |
| **Status** | Work in progress: not verified |
| **Generated** | {now.isoformat(timespec="minutes")} by KingmaDoc {__version__} |

> [!WARNING]
> **TODO: automatic verification is not implemented yet (planned for phase 2).**
> This file is a placeholder. KingmaDoc has not compared the plan with the code and has
> not run any build, test or lint command. Nothing below is checked; fill it in by hand
> or regenerate it once `verify` is complete.

## Deviations

_TODO: where the implementation differs from the plan (scope, containers, assumptions),
and why._

- _TODO_

## Validation results

_TODO: results of the checks that prove the feature works._

| Check | Command | Result |
|---|---|---|
| Build | _TODO_ | _not run_ |
| Tests | _TODO_ | _not run_ |
| Lint | _TODO_ | _not run_ |
"""
