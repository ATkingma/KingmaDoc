"""Writing generated documents to disk (shared by the plan and verify modes)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from kingmadoc.exceptions import GenerationError


def write_document(content: str, path: Path, overwrite: bool = False) -> Path:
    """Write ``content`` to ``path``, creating parent directories.

    Args:
        content: Document text.
        path: Destination file.
        overwrite: Replace an existing file if True.

    Returns:
        The written path.

    Raises:
        GenerationError: If the file exists (and ``overwrite`` is False) or cannot be written.
    """
    if path.exists() and not overwrite:
        raise GenerationError(f"{path} already exists (use --force to overwrite)")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise GenerationError(f"Cannot write {path}: {exc}") from exc
    return path


def write_documents(documents: Sequence[tuple[Path, str]], overwrite: bool = False) -> list[Path]:
    """Write several documents, or none of them if any target already exists.

    Args:
        documents: ``(path, content)`` pairs.
        overwrite: Replace existing files if True.

    Returns:
        The written paths, in input order.

    Raises:
        GenerationError: If a file exists (and ``overwrite`` is False) or cannot be written.
    """
    if not overwrite:
        existing = [str(path) for path, _ in documents if path.exists()]
        if existing:
            raise GenerationError(
                f"{', '.join(existing)} already exist{'s' if len(existing) == 1 else ''} "
                "(use --force to overwrite)"
            )
    return [write_document(content, path, overwrite=True) for path, content in documents]
