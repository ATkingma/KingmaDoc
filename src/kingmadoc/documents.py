"""Writing generated documents to disk (shared by the plan and verify modes).

Multi-file writes are all-or-nothing, in three phases:

1. Validate every target (not a directory; absent unless ``overwrite``) and create
   missing parent directories.
2. Write every document to a temporary file next to its target.
3. Move each temporary file over its target with :func:`os.replace`, keeping a backup
   of files that already existed.

If phase 2 or 3 fails, temporary files are deleted, replaced files are restored from
their backups, new files and newly created directories are removed, and the error is
raised as :class:`~kingmadoc.exceptions.GenerationError`.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Sequence
from pathlib import Path

from kingmadoc.exceptions import GenerationError


def write_document(path: Path, content: str, overwrite: bool = False) -> Path:
    """Write ``content`` to ``path``, creating parent directories.

    Args:
        path: Destination file.
        content: Document text.
        overwrite: Replace an existing file if True.

    Returns:
        The written path.

    Raises:
        GenerationError: If the file exists (and ``overwrite`` is False) or cannot be written.
    """
    return write_documents([(path, content)], overwrite=overwrite)[0]


def write_documents(documents: Sequence[tuple[Path, str]], overwrite: bool = False) -> list[Path]:
    """Write several documents, or none of them (see the module docstring).

    Args:
        documents: ``(path, content)`` pairs.
        overwrite: Replace existing files if True.

    Returns:
        The written paths, in input order.

    Raises:
        GenerationError: If validation fails or any file cannot be written; the
            filesystem is then left as it was.
    """
    created_dirs = _validate(documents, overwrite)
    temps: list[Path] = []
    replaced: list[tuple[Path, Path | None]] = []  # (target, backup or None if new)
    try:
        for path, content in documents:  # phase 2
            temp = _sibling(path, "tmp")
            temps.append(temp)
            with temp.open("x", encoding="utf-8") as handle:
                handle.write(content)
        for (path, _), temp in zip(documents, temps):  # phase 3
            backup = None
            if path.exists():
                backup = _sibling(path, "bak")
                os.replace(path, backup)
            replaced.append((path, backup))
            os.replace(temp, path)
    except OSError as exc:
        _roll_back(temps, replaced, created_dirs)
        raise GenerationError(f"Cannot write {len(documents)} document(s): {exc}") from exc
    for _, backup in replaced:
        if backup is not None:
            backup.unlink(missing_ok=True)
    return [path for path, _ in documents]


def _validate(documents: Sequence[tuple[Path, str]], overwrite: bool) -> list[Path]:
    """Phase 1: check every target, then create missing parents (returned for rollback)."""
    for path, _ in documents:
        if path.is_dir():
            raise GenerationError(f"Cannot write {path}: it is a directory")
    if not overwrite:
        existing = [str(path) for path, _ in documents if path.exists()]
        if existing:
            raise GenerationError(
                f"{', '.join(existing)} already exist{'s' if len(existing) == 1 else ''} "
                "(use --force to overwrite)"
            )
    created: list[Path] = []
    try:
        for path, _ in documents:
            missing = [p for p in reversed(path.parents) if not p.exists()]
            for directory in missing:
                directory.mkdir()
                created.append(directory)
    except OSError as exc:
        _remove_dirs(created)
        raise GenerationError(f"Cannot create {exc.filename}: {exc.strerror}") from exc
    return created


def _roll_back(
    temps: list[Path], replaced: list[tuple[Path, Path | None]], created_dirs: list[Path]
) -> None:
    """Best-effort undo of phases 2 and 3."""
    for path, backup in reversed(replaced):
        try:
            if backup is not None:
                os.replace(backup, path)
            else:
                path.unlink(missing_ok=True)
        except OSError:
            pass
    for temp in temps:
        temp.unlink(missing_ok=True)
    _remove_dirs(created_dirs)


def _remove_dirs(directories: list[Path]) -> None:
    for directory in reversed(directories):
        try:
            directory.rmdir()  # only succeeds if still empty
        except OSError:
            pass


def _sibling(path: Path, kind: str) -> Path:
    """A hidden, unique file name next to ``path`` (same directory, so renames are atomic)."""
    return path.with_name(f".{path.name}.{secrets.token_hex(4)}.{kind}")
