"""The agent skills that ship with KingmaDoc, and installing them into a project.

``kingmadoc skills install`` copies them into the agent's native skills directory (Agent
Skills standard), so ``pip install kingmadoc`` is the only manual step.

Each installed skill folder gets a manifest (:data:`MANIFEST`) with the SHA-256 of every
file as installed. A later install compares against it: a file that still matches is an
older KingmaDoc version and is updated; a file that differs is a local edit and is only
replaced with ``force``. Installs from before the manifest are recognised by
:data:`PREVIOUS_RELEASES`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
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

MANIFEST = ".kingmadoc-skill.json"
# "<skill>/<file>" -> SHA-256 of every version shipped before the manifest existed
# (up to commit 29244f7). Frozen: later versions are recorded in each install's manifest.
PREVIOUS_RELEASES: Mapping[str, frozenset[str]] = MappingProxyType({
    "kingmadoc/SKILL.md": frozenset({
        "01f1bac9065908d1c51d7c9a170086fc53152b1ec2a1b49adeec4c483b9b2c3f",
        "2b0472a10a0fa44158f6c3890f6ffb1dc12223afbf98dfb93c5061e6a28b0bb2",
        "670d296a3ccf0a83e36d33422bcd1f0a28e159bf1c3a6cb5e4ab678130f58878",
        "6aec4d093d462c710c3959906276e341fd155ea43f0fb15ffda7df8526cf5940",
    }),
    "explaining-code/SKILL.md": frozenset({
        "228fefff6f2cd2c49cc459b5e3744833ba15972cac4900ddfe01244680906196",
        "27794db4904075b7bee3a487e5672377141f98fa518cbf5f4a468ffc2c89c179",
        "6f0b7b312215aaceef9f71994da75b29cb2464ff844e7f1026afec688a9017dd",
        "9d22a56075b475c732d455a5b0253192dfad614c0315c77a291c2b91848390ca",
        "a13ede0346fb6be09860530fb044835654ea39b113b7ffb84d674ed4658a7419",
    }),
    "explaining-code/reference/arc42.md": frozenset({
        "fc7b104a067a900ad8479c2ac46960a5dd9cb6e017163e15b5fb5782e279a728",
    }),
    "explaining-code/reference/c4.md": frozenset({
        "c95bfba9a5c2522eeb096ad4584aa9708885f17eb27e7a96d0a76aafa7f05b4d",
    }),
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


def bundled_files(name: str) -> list[tuple[Path, Path]]:
    """Return every file of a bundled skill as ``(path inside the skill folder, source)``.

    Args:
        name: One of :data:`SKILL_NAMES`.

    Returns:
        ``SKILL.md`` plus any other files of the skill (e.g. ``reference/*.md``), sorted.

    Raises:
        KingmaDocError: If the skill is unknown or missing from the installation.
    """
    skill_md = bundled_skill(name)
    if name == "kingmadoc":  # skill/ also holds the other skills and the agent variants
        return [(Path("SKILL.md"), skill_md)]
    folder = skill_md.parent
    return sorted((f.relative_to(folder), f) for f in folder.rglob("*") if f.is_file())


@dataclass(frozen=True)
class InstallResult:
    """What :func:`install_skills` did."""

    written: tuple[Path, ...]
    up_to_date: tuple[Path, ...]
    removed: tuple[Path, ...]


def install_skills(root: Path, agent: str, force: bool = False) -> InstallResult:
    """Copy every bundled skill folder into ``<root>/<agent dir>/<name>/``.

    Files an earlier KingmaDoc installed (still unchanged) are updated, and files it
    installed that the skill no longer ships are removed; local edits are kept.

    Args:
        root: Project root.
        agent: Key of :data:`AGENT_DIRS`.
        force: Also replace installed skill files with local edits.

    Returns:
        The written, already up-to-date and removed paths.

    Raises:
        KingmaDocError: On an unknown agent, or on locally edited skill files without
            ``force``.
    """
    if agent not in AGENT_DIRS:
        raise KingmaDocError(f"Unknown agent {agent!r}; supported: {', '.join(AGENT_DIRS)}")
    base = root / AGENT_DIRS[agent]
    pending: list[tuple[Path, str]] = []
    current: list[Path] = []
    changed: list[str] = []
    stale: list[Path] = []
    for name in SKILL_NAMES:
        folder = base / name
        installed = _read_manifest(folder / MANIFEST)
        hashes: dict[str, str] = {}
        for relative, source in bundled_files(name):
            key = relative.as_posix()
            target = folder / relative
            content = source.read_text(encoding="utf-8")
            hashes[key] = _sha256(content)
            found = _sha256(_read(target)) if target.is_file() else None
            if found == hashes[key]:
                current.append(target)
                continue
            known = PREVIOUS_RELEASES.get(f"{name}/{key}", frozenset())
            if key in installed:
                known = known | {installed[key]}
            if target.exists() and not force and found not in known:
                changed.append(str(target))
            pending.append((target, content))
        for key, digest in installed.items():
            old = _inside(folder, key)
            if (
                key not in hashes
                and old is not None
                and old.is_file()
                and _sha256(_read(old)) == digest
            ):
                stale.append(old)
        manifest = json.dumps({"skill": name, "files": hashes}, indent=2, sort_keys=True)
        if installed != hashes:
            pending.append((folder / MANIFEST, manifest + "\n"))
    if changed:
        raise KingmaDocError(
            f"{', '.join(changed)} changed locally since KingmaDoc installed them; "
            "use --force to replace them with the bundled version"
        )
    written = write_documents(pending, overwrite=True)
    for path in stale:
        try:
            path.unlink()
        except OSError as exc:
            raise KingmaDocError(f"Cannot remove {path}: {exc.strerror}") from exc
    return InstallResult(
        written=tuple(p for p in written if p.name != MANIFEST),
        up_to_date=tuple(current),
        removed=tuple(stale),
    )


def _inside(folder: Path, key: str) -> Path | None:
    """``folder / key`` if it stays inside ``folder``; None for ``..``, absolute or odd keys.

    The manifest is part of the repository, so it is not trusted to name paths.
    """
    parts = PurePosixPath(key).parts
    if not parts or key.startswith("/") or "\\" in key or ":" in key or ".." in parts:
        return None
    path = folder.joinpath(*parts)
    try:
        path.resolve().relative_to(folder.resolve())
    except ValueError:
        return None
    return path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _sha256(text: str) -> str:
    """Hash text independent of line endings (Windows writes CRLF)."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _read_manifest(path: Path) -> dict[str, str]:
    """The installed files and their hashes; empty when missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict):
        return {}
    return {k: v for k, v in files.items() if isinstance(k, str) and isinstance(v, str)}
