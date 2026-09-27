"""Make VS Code open KingmaDoc explainers as a rendered Markdown preview.

VS Code normally opens ``.md`` files as source text; a workspace setting
(``workbench.editorAssociations``) can open matching files in the built-in Markdown
preview instead, so the pictures are visible immediately. Only ``docs/explain/`` is
associated; other Markdown files keep opening as text.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from kingmadoc.documents import write_document

SETTING = "workbench.editorAssociations"
PREVIEW_PATTERN = "**/docs/explain/**/*.md"
EDITOR_ID = "vscode.markdown.preview.editor"


def user_settings_path(platform: str | None = None) -> Path:
    """Return VS Code's user settings file (applies to every folder and loose file).

    Args:
        platform: ``sys.platform`` value; None for the current one.

    Returns:
        ``settings.json`` in the VS Code user folder of this platform.
    """
    platform = platform or sys.platform
    if platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "Code" / "User" / "settings.json"


def enable_user_markdown_preview() -> str:
    """Add the preview association to VS Code's user settings (see :func:`user_settings_path`).

    Returns:
        A one-line message saying what was done (or what to add by hand).
    """
    return _enable(user_settings_path())


def enable_markdown_preview(root: Path) -> str:
    """Add the preview association to ``<root>/.vscode/settings.json`` when it is safe.

    Existing settings are kept. A settings file that is not plain JSON (VS Code allows
    comments and trailing commas) is never rewritten, and a different choice the user
    made for the same pattern is left alone.

    Args:
        root: Project root.

    Returns:
        A one-line message saying what was done (or what to add by hand).
    """
    return _enable(root / ".vscode" / "settings.json")


def _enable(path: Path) -> str:
    manual = f'add "{SETTING}": {{"{PREVIEW_PATTERN}": "{EDITOR_ID}"}} to {path} yourself'
    data: dict[str, object] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return f"{path} has comments or is not plain JSON, so it was not changed; {manual}."
        if not isinstance(loaded, dict):
            return f"{path} is not a JSON object, so it was not changed; {manual}."
        data = loaded
    associations = data.get(SETTING, {})
    if not isinstance(associations, dict):
        return f"{SETTING} in {path} is not an object, so it was not changed; {manual}."
    current = associations.get(PREVIEW_PATTERN)
    if current == EDITOR_ID:
        return "VS Code already opens explainers (docs/explain/) as a rendered preview."
    if current is not None:
        return f"{PREVIEW_PATTERN} is associated with {current!r} in {path}; left unchanged."
    data[SETTING] = {**associations, PREVIEW_PATTERN: EDITOR_ID}
    write_document(path, json.dumps(data, indent=2) + "\n", overwrite=True)
    return f"VS Code now opens explainers (docs/explain/) as a rendered preview ({path})."


def preview_enabled(root: Path) -> bool:
    """Tell whether VS Code already opens this project's explainers as a preview.

    Args:
        root: Project root.

    Returns:
        True if the association is set in the project's or the user's settings (to the
        preview or to another editor the user chose).
    """
    return _associated(root / ".vscode" / "settings.json") or _associated(user_settings_path())


def _associated(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    associations = data.get(SETTING) if isinstance(data, dict) else None
    return isinstance(associations, dict) and PREVIEW_PATTERN in associations
