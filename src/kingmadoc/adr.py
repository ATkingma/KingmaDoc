"""Architecture Decision Records: ``kingmadoc adr "<title>"`` → ``docs/adr/<NNNN>-<slug>.md``."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from jinja2 import TemplateError

from kingmadoc.config import FeatureDocConfig
from kingmadoc.exceptions import AdrError
from kingmadoc.naming import slugify
from kingmadoc.templating import load_template

ADR_DIR = Path("docs/adr")
ADR_TEMPLATE = "adr.md.j2"
STATUSES: tuple[str, ...] = ("proposed", "accepted", "rejected", "superseded")

# Zero-padded to four digits (the common ADR convention); wider numbers keep sorting
# correctly up to 9999 and still parse beyond it.
NUMBER_WIDTH = 4
ADR_FILE = re.compile(r"(\d+)-.+\.md")
# Numbers in this range look like years ("2024-q3-review.md"); such files only count as
# ADRs when their first line is an ADR heading with that number ("# 2024. ...").
YEAR_LIKE = range(1900, 2101)


def next_number(existing_names: Iterable[str]) -> int:
    """Return the number for a new ADR: one above the highest existing number.

    Numbers are never reused, even when an ADR was deleted, so links stay stable.

    Args:
        existing_names: File names in the ADR directory.

    Returns:
        ``1`` if there are no ADRs yet.

    Example:
        >>> next_number(["0001-use-postgres.md", "0003-drop-redis.md", "README.md"])
        4
    """
    numbers = [int(m.group(1)) for n in existing_names if (m := ADR_FILE.fullmatch(n))]
    return max(numbers, default=0) + 1


def adr_filename(number: int, title: str) -> str:
    """Return ``<NNNN>-<slug>.md`` for an ADR.

    Args:
        number: ADR number.
        title: ADR title (the slug is derived from it).

    Returns:
        The file name.

    Example:
        >>> adr_filename(7, "Use PostgreSQL for user data")
        '0007-use-postgresql-for-user-data.md'
    """
    return f"{number:0{NUMBER_WIDTH}d}-{slugify(title)}.md"


def render_adr(
    root: Path,
    number: int,
    title: str,
    *,
    status: str = "proposed",
    today: date,
    template: str = ADR_TEMPLATE,
) -> str:
    """Render an ADR in the standard format (title, date, status, context, decision,
    consequences). Pure apart from reading the template; the caller passes the date.

    Args:
        root: Project root (for project-local templates).
        number: ADR number.
        title: Decision title.
        status: One of :data:`STATUSES`.
        today: Date of the decision record.
        template: Bundled template name or explicit path (``adr.template`` in the config).

    Returns:
        The rendered Markdown document.

    Raises:
        ConfigError: If the configured template path does not exist or is not a file.
        AdrError: If the title is blank, the status unknown, or the template fails.
    """
    title = " ".join(title.split())
    if not title:
        raise AdrError("The ADR title must not be empty")
    if status not in STATUSES:
        raise AdrError(f"Unknown ADR status {status!r}; use one of {', '.join(STATUSES)}")
    try:
        return load_template(template, root).render(
            number=f"{number:0{NUMBER_WIDTH}d}",
            title=title,
            status=status,
            statuses=STATUSES,
            date=today.isoformat(),
        )
    except TemplateError as exc:
        raise AdrError(f"Cannot render template {template!r}: {exc}") from exc


def adr_path(root: Path, config: FeatureDocConfig, title: str) -> tuple[int, Path]:
    """Pick the number and path for a new ADR in ``<root>/docs/adr``.

    Args:
        root: Project root.
        config: KingmaDoc configuration.
        title: ADR title.

    Returns:
        ``(number, path)``.

    Raises:
        AdrError: If ADRs are not enabled in the config.
    """
    if not config.adr.enabled:
        raise AdrError(
            "ADRs are disabled. Enable them in .featuredoc.yml:\n  adr:\n    enabled: true"
        )
    directory = root / ADR_DIR
    names = [p.name for p in directory.iterdir() if _is_adr(p)] if directory.is_dir() else []
    number = next_number(names)
    return number, directory / adr_filename(number, title)


def _is_adr(path: Path) -> bool:
    """Whether ``path`` is an ADR (see :data:`YEAR_LIKE` for date-named files)."""
    match = ADR_FILE.fullmatch(path.name)
    if not match or not path.is_file():
        return False
    number = int(match.group(1))
    if number not in YEAR_LIKE:
        return True
    try:
        with path.open(encoding="utf-8", errors="ignore") as handle:
            first_line = handle.readline()
    except OSError:
        return False
    return re.match(rf"#\s*0*{number}\b", first_line) is not None
