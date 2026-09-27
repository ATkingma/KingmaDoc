"""Where a feature's plan and verification docs are (``<output_dir>/<slug>-plan.md``)."""

from __future__ import annotations

import re
from pathlib import Path

from kingmadoc.config import FeatureDocConfig, resolve_output_dir
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
        ConfigError: If ``output_dir`` resolves outside the project root.
        VerificationError: If the slug is malformed or the plan doc does not exist.
    """
    if not SLUG_PATTERN.fullmatch(slug):
        raise VerificationError(
            f"Invalid feature slug {slug!r}: use lowercase letters, digits and hyphens "
            f"(the part before {PLAN_SUFFIX!r})"
        )
    plan_dir = resolve_output_dir(root, config)
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
