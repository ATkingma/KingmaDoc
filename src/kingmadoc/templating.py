"""Locating and loading the Jinja2 templates that ship with KingmaDoc."""

from __future__ import annotations

from importlib.resources import files as package_files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


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
        Path(__file__).resolve().parents[2] / "templates",  # editable/source checkout
    ]
    return [d for d in candidates if d.is_dir()]


def environment(root: Path) -> Environment:
    """Jinja2 environment for Markdown templates found via :func:`template_dirs`.

    Uses ``StrictUndefined``, so every template variable must be passed.

    Args:
        root: Project root.

    Returns:
        A configured environment.
    """
    return Environment(
        loader=FileSystemLoader([str(d) for d in template_dirs(root)]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,  # Markdown output, not HTML.
    )
