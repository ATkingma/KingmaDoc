"""Locating and loading the Jinja2 templates KingmaDoc renders.

Security model: ``kingmadoc`` is often run inside repositories nobody reviewed (by an
agent, in a fresh clone). So

- bundled templates are loaded only from the installed package (:data:`BUNDLED_DIR`);
  the analyzed project's root is never searched;
- a project template is used only when ``.featuredoc.yml`` names it explicitly as a
  path, and
- every template runs in Jinja's :class:`~jinja2.sandbox.SandboxedEnvironment`, so even
  an explicitly configured template cannot reach Python internals (``os``, ``__class__``).
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import FileSystemLoader, StrictUndefined, Template
from jinja2.sandbox import SandboxedEnvironment

from kingmadoc.exceptions import ConfigError

BUNDLED_DIR = Path(__file__).resolve().parent / "templates"


def resolve_template(template: str, root: Path) -> tuple[Path, str]:
    """Find the directory and file name for a configured template.

    A plain file name of a bundled template (e.g. ``plan_default.md.j2``) selects the
    bundled one. Anything else is a path relative to the project root (or absolute),
    e.g. ``./docs/my_plan.md.j2``; it is never looked up implicitly.

    Args:
        template: Value of a ``template`` setting.
        root: Project root.

    Returns:
        ``(directory, file_name)`` to load the template from.

    Raises:
        ConfigError: If a template path does not exist or is not a file.
    """
    if "/" not in template and "\\" not in template and (BUNDLED_DIR / template).is_file():
        return BUNDLED_DIR, template
    path = root / template
    if not path.exists():
        raise ConfigError(f"Template {template!r} does not exist (looked for {path})")
    if not path.is_file():
        raise ConfigError(f"Template {template!r} is not a file ({path})")
    path = path.resolve()
    return path.parent, path.name


def environment(directory: Path) -> SandboxedEnvironment:
    """Sandboxed Jinja2 environment that loads templates from ``directory`` only.

    Uses ``StrictUndefined``, so every template variable must be passed.

    Args:
        directory: Directory containing the template(s).

    Returns:
        A configured sandboxed environment.
    """
    return SandboxedEnvironment(
        loader=FileSystemLoader(str(directory)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,  # Markdown output, not HTML.
    )


def load_template(template: str, root: Path) -> Template:
    """Resolve and load a configured template in a sandboxed environment.

    Args:
        template: Bundled template name or explicit template path.
        root: Project root.

    Returns:
        The compiled template.

    Raises:
        ConfigError: If a template path does not exist or is not a file.
        jinja2.TemplateError: If the template cannot be loaded or compiled.
    """
    directory, name = resolve_template(template, root)
    return environment(directory).get_template(name)
