"""Render D2 diagrams in Markdown documents to SVG images (``kingmadoc render``; WP11).

Every fenced ``d2`` block becomes two files next to the document, ``img/<doc>-<n>.svg``
(the picture) and ``img/<doc>-<n>.d2`` (its source), and the block in the document is
replaced by only the image, preceded by an HTML comment that points to the source::

    <!-- kingmadoc:diagram img/<doc>-<n>.d2 -->
    ![<nearest heading>](img/<doc>-<n>.svg)

The comment is invisible in Markdown previews. To change a diagram, edit its ``.d2`` file
(or put a new ``d2`` block in the document) and render again. Documents rendered by the
earlier format (source folded in ``<details>``) are converted.

Only D2 is rendered; :func:`kingmadoc.d2_binary.ensure_d2` finds it or downloads the
pinned release once, so nothing has to be installed besides KingmaDoc.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

from kingmadoc.documents import write_document
from kingmadoc.exceptions import RenderError
from kingmadoc.explain import EXPLAINER_FILE, index_path

# Seconds per diagram; D2's own default is 120, but diagrams in docs are small.
D2_TIMEOUT = 60
# Pixels around each image; D2's default of 100 wastes space in a document.
D2_PAD = 20

# A diagram is either a fenced d2 block, or a reference written by an earlier render.
# References may only point into img/ next to the document (no other paths).
_ITEM = re.compile(
    r"^```d2\n(?P<inline>.*?)\n```$"
    r"|^<!-- kingmadoc:diagram (?P<ref>img/[\w.-]+\.d2) -->\n!\[[^\]\n]*\]\([^)\n]*\)$",
    re.S | re.M,
)
# The earlier format: image + source folded in <details>, between two markers.
_LEGACY = re.compile(
    r"<!-- kingmadoc:render -->\n.*?(^```d2\n.*?\n```$).*?<!-- /kingmadoc:render -->",
    re.S | re.M,
)
_HEADING = re.compile(r"^#{1,6} +(.+?) *$", re.M)


def render_file(path: Path, d2: Sequence[str]) -> list[Path]:
    """Render every D2 diagram in a Markdown file to an SVG and embed only the images.

    All diagrams are rendered before anything is written: if one fails, neither the
    document nor any file in ``img/`` changes.

    Args:
        path: The Markdown document.
        d2: Command that runs D2 (see :func:`kingmadoc.d2_binary.ensure_d2`).

    Returns:
        The written image paths, in document order (empty if there are no diagrams).

    Raises:
        RenderError: If D2 cannot be run, a diagram does not compile, or a referenced
            ``.d2`` source file is missing.
    """
    text = _LEGACY.sub(lambda m: m.group(1), path.read_text(encoding="utf-8"))
    items = list(_ITEM.finditer(text))
    if not items:
        return []

    image_dir = path.parent / "img"
    sources = [_source(item, path) for item in items]
    stem = _image_stem(path)
    names = [f"{stem}-{n}" for n in range(1, len(items) + 1)]
    # Next to the document, not in the system temp dir: os.replace cannot move the images
    # across filesystems (EXDEV when /tmp is another disk).
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".kingmadoc-render-") as tmp:
        rendered = [
            _render(source, Path(tmp), n, path, d2)
            for n, source in enumerate(sources, start=1)
        ]
        image_dir.mkdir(parents=True, exist_ok=True)
        for name, source, svg in zip(names, sources, rendered, strict=True):
            write_document(image_dir / f"{name}.d2", source.rstrip("\n") + "\n", overwrite=True)
            os.replace(svg, image_dir / f"{name}.svg")
    _remove_stale_files(image_dir, stem, set(names))
    _remove_renamed_files(image_dir, path, items, set(names))

    for item, name in zip(reversed(items), reversed(names), strict=True):
        alt = _nearest_heading(text, item.start()) or "Diagram"
        text = text[: item.start()] + _embed(alt, name) + text[item.end() :]
    write_document(path, text, overwrite=True)
    return [image_dir / f"{name}.svg" for name in names]


def _source(item: re.Match[str], doc: Path) -> str:
    """The D2 source of one diagram: inline in the document, or in its referenced file."""
    if item.group("inline") is not None:
        return item.group("inline")
    reference = doc.parent / item.group("ref")
    try:
        return reference.read_text(encoding="utf-8")
    except OSError as exc:
        raise RenderError(
            f"{doc} refers to {item.group('ref')}, but that diagram source cannot be read: "
            f"{exc.strerror}"
        ) from exc


def _render(source: str, tmp: Path, n: int, doc: Path, d2: Sequence[str]) -> Path:
    src, out = tmp / f"{n}.d2", tmp / f"{n}.svg"
    src.write_text(source + "\n", encoding="utf-8")
    command = [*d2, "--pad", str(D2_PAD), str(src), str(out)]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=D2_TIMEOUT, check=False
        )
    except FileNotFoundError as exc:
        raise RenderError(f"Cannot run D2 ({d2[0]}): {exc.strerror}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderError(f"D2 timed out on diagram {n} in {doc}") from exc
    if result.returncode != 0 or not out.is_file():
        detail = " ".join(line.strip() for line in result.stderr.splitlines()[-3:])
        # D2 reports the temporary file name; the diagram number is what the reader needs.
        detail = detail.replace(str(src), f"diagram {n}")
        raise RenderError(f"D2 could not render diagram {n} in {doc}: {detail}")
    return out


def _embed(alt: str, name: str) -> str:
    alt = alt.replace("[", "(").replace("]", ")")
    return f"<!-- kingmadoc:diagram img/{name}.d2 -->\n![{alt}](img/{name}.svg)"


def _nearest_heading(text: str, position: int) -> str | None:
    headings = [m.group(1) for m in _HEADING.finditer(text, 0, position)]
    return headings[-1] if headings else None


def _image_stem(doc: Path) -> str:
    """Images are named after the document; an explainer folder's README uses ``figure``.

    Only there: elsewhere a README.md and an index.md can share one ``img/`` folder.
    """
    if doc.name.lower() == EXPLAINER_FILE.lower() and index_path(doc) is not None:
        return "figure"
    return doc.stem


def _remove_renamed_files(
    image_dir: Path, doc: Path, items: Sequence[re.Match[str]], keep: set[str]
) -> None:
    """Delete this document's own files that it referred to under a name it no longer uses.

    E.g. ``img/README-1.*`` of an explainer rendered before its images became ``figure-1``.
    Only the document's own names (``<doc>-<n>``, ``figure-<n>``) are touched.
    """
    own = re.compile(rf"(?:{re.escape(doc.stem)}|figure)-\d+")
    for item in items:
        ref = item.group("ref")
        name = Path(ref).stem if ref else ""
        if name in keep or not own.fullmatch(name):
            continue
        for suffix in (".svg", ".d2"):
            (image_dir / f"{name}{suffix}").unlink(missing_ok=True)


def _remove_stale_files(image_dir: Path, stem: str, keep: set[str]) -> None:
    """Delete images and sources of this document's diagrams that no longer exist."""
    pattern = re.compile(rf"({re.escape(stem)}-\d+)\.(svg|d2)")
    for file in image_dir.iterdir():
        match = pattern.fullmatch(file.name)
        if match and match.group(1) not in keep:
            file.unlink()
