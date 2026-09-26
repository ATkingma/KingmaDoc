"""Render D2 diagrams in Markdown documents to SVG images (``kingmadoc render``; WP11).

Every fenced ``d2`` block becomes ``img/<document>-<n>.svg`` next to the document. The
image is embedded above the block, and the block is kept below it in a collapsed
``<details>`` element: people see the picture, agents (and editors) keep the text.
Rendering again replaces the images, so editing the D2 source and re-running is enough.

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

# Seconds per diagram; D2's own default is 120, but diagrams in docs are small.
D2_TIMEOUT = 60
# Pixels around each image; D2's default of 100 wastes space in a document.
D2_PAD = 20

_BLOCK = re.compile(r"^```d2\n(.*?)\n```$", re.S | re.M)
_MANAGED = re.compile(
    r"<!-- kingmadoc:render -->\n.*?(^```d2\n.*?\n```$).*?<!-- /kingmadoc:render -->",
    re.S | re.M,
)
_HEADING = re.compile(r"^#{1,6} +(.+?) *$", re.M)


def render_file(path: Path, d2: Sequence[str]) -> list[Path]:
    """Render every D2 block in a Markdown file to an SVG and embed the images.

    All diagrams are rendered before anything is written: if one fails, neither the
    document nor any image changes.

    Args:
        path: The Markdown document.
        d2: Command that runs D2 (see :func:`kingmadoc.d2_binary.ensure_d2`).

    Returns:
        The written image paths, in document order (empty if there are no D2 blocks).

    Raises:
        RenderError: If D2 cannot be run or a diagram does not compile.
    """
    text = _MANAGED.sub(lambda m: m.group(1), path.read_text(encoding="utf-8"))
    blocks = list(_BLOCK.finditer(text))
    if not blocks:
        return []

    image_dir = path.parent / "img"
    names = [f"{path.stem}-{n}.svg" for n in range(1, len(blocks) + 1)]
    with tempfile.TemporaryDirectory() as tmp:
        rendered = [
            _render(block.group(1), Path(tmp), n, path, d2)
            for n, block in enumerate(blocks, start=1)
        ]
        image_dir.mkdir(parents=True, exist_ok=True)
        images = [image_dir / name for name in names]
        for source, target in zip(rendered, images, strict=True):
            os.replace(source, target)
    _remove_stale_images(image_dir, path.stem, set(names))

    for block, name in zip(reversed(blocks), reversed(names), strict=True):
        alt = _nearest_heading(text, block.start()) or "Diagram"
        text = text[: block.start()] + _embed(block.group(0), alt, name) + text[block.end() :]
    write_document(path, text, overwrite=True)
    return images


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


def _embed(block: str, alt: str, name: str) -> str:
    alt = alt.replace("[", "(").replace("]", ")")
    return (
        "<!-- kingmadoc:render -->\n"
        f"![{alt}](img/{name})\n\n"
        "<details>\n<summary>Diagram source (D2)</summary>\n\n"
        f"{block}\n\n"
        "</details>\n"
        "<!-- /kingmadoc:render -->"
    )


def _nearest_heading(text: str, position: int) -> str | None:
    headings = [m.group(1) for m in _HEADING.finditer(text, 0, position)]
    return headings[-1] if headings else None


def _remove_stale_images(image_dir: Path, stem: str, keep: set[str]) -> None:
    pattern = re.compile(rf"{re.escape(stem)}-\d+\.svg")
    for image in image_dir.iterdir():
        if pattern.fullmatch(image.name) and image.name not in keep:
            image.unlink()
