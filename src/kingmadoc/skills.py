"""The agent skills that ship with KingmaDoc, and installing them into a project.

``kingmadoc skills install`` copies them into the agent's native skills directory (Agent
Skills standard), so ``pip install kingmadoc`` is the only manual step.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from kingmadoc.documents import write_documents
from kingmadoc.exceptions import KingmaDocError

SKILL_NAMES: tuple[str, ...] = ("kingmadoc", "explaining-code")
# Agent -> skills directory relative to the project root (one folder per skill inside).
AGENT_DIRS: Mapping[str, str] = MappingProxyType({
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "codex": ".agents/skills",
    "copilot": ".github/skills",
})

# In an installed wheel the skills are package data (hatch force-include); in a source
# checkout or editable install they are read from the repository's skill/ directory.
_PACKAGED = Path(__file__).resolve().parent / "skills"
_CHECKOUT = Path(__file__).resolve().parents[2] / "skill"


def bundled_skill(name: str) -> Path:
    """Return the path of a bundled skill's ``SKILL.md``.

    Args:
        name: One of :data:`SKILL_NAMES`.

    Returns:
        The file shipped in the package, or in the source checkout.

    Raises:
        KingmaDocError: If the skill is unknown or missing from the installation.
    """
    if name not in SKILL_NAMES:
        raise KingmaDocError(f"Unknown skill {name!r}; available: {', '.join(SKILL_NAMES)}")
    candidates = [_PACKAGED / name / "SKILL.md"]
    checkout = _CHECKOUT / "SKILL.md" if name == "kingmadoc" else _CHECKOUT / name / "SKILL.md"
    candidates.append(checkout)
    for path in candidates:
        if path.is_file():
            return path
    raise KingmaDocError(f"Skill {name!r} is missing from this KingmaDoc installation")


def install_skills(root: Path, agent: str, force: bool = False) -> tuple[list[Path], list[Path]]:
    """Copy every bundled skill into ``<root>/<agent dir>/<name>/SKILL.md``.

    Args:
        root: Project root.
        agent: Key of :data:`AGENT_DIRS`.
        force: Replace installed skills that differ (e.g. local edits).

    Returns:
        ``(written, up_to_date)`` paths.

    Raises:
        KingmaDocError: On an unknown agent, or on changed installed skills without ``force``.
    """
    if agent not in AGENT_DIRS:
        raise KingmaDocError(f"Unknown agent {agent!r}; supported: {', '.join(AGENT_DIRS)}")
    base = root / AGENT_DIRS[agent]
    pending: list[tuple[Path, str]] = []
    current: list[Path] = []
    changed: list[str] = []
    for name in SKILL_NAMES:
        target = base / name / "SKILL.md"
        content = bundled_skill(name).read_text(encoding="utf-8")
        if target.is_file() and target.read_text(encoding="utf-8") == content:
            current.append(target)
            continue
        if target.exists() and not force:
            changed.append(str(target))
        pending.append((target, content))
    if changed:
        raise KingmaDocError(
            f"{', '.join(changed)} differ from the bundled version (local edits or another "
            "KingmaDoc version); use --force to replace them"
        )
    return write_documents(pending, overwrite=True), current
