"""Render D2 diagrams in Markdown documents to SVG images (``kingmadoc render``; WP11).

Every fenced ``d2`` block becomes two files next to the document, ``img/<doc>-<n>.svg``
(the picture) and ``img/<doc>-<n>.d2`` (its source), and the block in the document is
replaced by only the image, preceded by an HTML comment that points to the source::

    <!-- kingmadoc:diagram img/<doc>-<n>.d2 -->
    ![<nearest heading>](data:image/png;base64,...)

By default the image is embedded as a base64 data URI, so the document shows its
pictures on its own; ``link=True`` (``--link``) links ``img/<doc>-<n>.png`` instead. The
files in ``img/`` are written either way, and a second render replaces the image line.

The comment is invisible in Markdown previews. To change a diagram, edit its ``.d2`` file
(or put a new ``d2`` block in the document) and render again. Documents rendered by the
earlier format (source folded in ``<details>``) are converted.

Only D2 is rendered; :func:`kingmadoc.d2_binary.ensure_d2` finds it or downloads the
pinned release once, so nothing has to be installed besides KingmaDoc.
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from types import MappingProxyType

from kingmadoc.documents import write_document
from kingmadoc.exceptions import RenderError
from kingmadoc.explain import EXPLAINER_FILE, index_path
from kingmadoc.raster import svg_to_png

# Seconds per diagram; D2's own default is 120, but diagrams in docs are small.
D2_TIMEOUT = 60
# Pixels around each image; D2's default of 100 wastes space in a document.
D2_PAD = 20
IMAGE_MODE = 0o644
# What `kingmadoc render` links in the document (PNG shows in every Markdown viewer).
IMAGE_FORMATS: tuple[str, ...] = ("png", "svg")
# D2's own dark theme; the SVG switches to it when the viewer uses dark mode.
D2_DARK_THEME = 200
# Straight, right-angled arrows (see _layout_args); bundled with D2 like dagre.
LAYOUT_ENGINE = "elk"
# Above this many arrows a figure gets hard to follow (render warns).
MAX_ARROWS = 12
# More words than this on one arrow label crowd the figure (a `[protocol]` counts as one).
MAX_LABEL_WORDS = 4
_LABEL = re.compile(
    r'^\s*[\w.]+\s*(?:<->|->|<-|--)\s*[\w.]+\s*:\s*(?P<label>"(?:[^"\\\n]|\\.)*"|[^{\n]*)',
    re.M,
)
# Media types of the embedded images.
_MEDIA_TYPES = MappingProxyType({"png": "image/png", "svg": "image/svg+xml"})
_ARROW = re.compile(r"^\s*([\w.]+)\s*(<->|->|<-|--)\s*([\w.]+)", re.M)
_LEGEND = re.compile(r"vars:\s*\{\s*d2-legend:\s*\{.*?^\s*\}\s*^\}", re.S | re.M)

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


def render_file(
    path: Path,
    d2: Sequence[str],
    dark: bool = True,
    image_format: str = "png",
    link: bool = False,
) -> list[Path]:
    """Render every D2 diagram in a Markdown file to images and embed only the images.

    Each diagram becomes ``img/<name>.svg`` (with a dark theme) and, for
    ``image_format="png"``, ``img/<name>.png`` too; the document links the chosen format.
    PNG shows in every Markdown viewer (VS Code, Visual Studio, Rider, GitHub, GitLab,
    Bitbucket); several block or mishandle SVG.

    All diagrams are rendered before anything is written: if one fails, neither the
    document nor any file in ``img/`` changes. A diagram whose PNG conversion fails is
    linked as SVG instead, so the document always shows every picture.

    Args:
        path: The Markdown document.
        d2: Command that runs D2 (see :func:`kingmadoc.d2_binary.ensure_d2`).
        dark: Also embed a dark theme in the SVG, used when the viewer is in dark mode.
        image_format: What the document shows: one of :data:`IMAGE_FORMATS`.
        link: Link the image file instead of embedding it as a base64 data URI.

    Returns:
        The linked image paths, in document order (empty if there are no diagrams); a
        ``.svg`` among them for ``image_format="png"`` means its PNG conversion failed.

    Raises:
        RenderError: If D2 cannot be run, a diagram does not compile, or a referenced
            ``.d2`` source file is missing.
    """
    text = _LEGACY.sub(lambda m: m.group(1), path.read_text(encoding="utf-8"))
    items = list(_ITEM.finditer(text))
    if not items:
        return []

    if image_format not in IMAGE_FORMATS:
        raise RenderError(f"Unknown image format {image_format!r}; use {', '.join(IMAGE_FORMATS)}")
    image_dir = path.parent / "img"
    sources = [_source(item, path) for item in items]
    stem = _image_stem(path)
    names = [f"{stem}-{n}" for n in range(1, len(items) + 1)]
    # Next to the document, not in the system temp dir: os.replace cannot move the images
    # across filesystems (EXDEV when /tmp is another disk).
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".kingmadoc-render-") as tmp:
        rendered = [
            _render(source, Path(tmp), n, path, [*d2, *_theme_args(dark), *_layout_args(source)])
            for n, source in enumerate(sources, start=1)
        ]
        # A diagram whose PNG fails keeps its SVG: a document never ends up without pictures.
        formats = [image_format] * len(rendered)
        if image_format == "png":
            for index, svg in enumerate(rendered):
                try:
                    png = svg_to_png(svg.read_text(encoding="utf-8"))
                except RenderError:
                    formats[index] = "svg"
                    continue
                svg.with_suffix(".png").write_bytes(png)
        image_dir.mkdir(parents=True, exist_ok=True)
        for name, source, svg, linked in zip(names, sources, rendered, formats, strict=True):
            write_document(image_dir / f"{name}.d2", source.rstrip("\n") + "\n", overwrite=True)
            for suffix in (".svg", ".png") if linked == "png" else (".svg",):
                target = image_dir / f"{name}{suffix}"
                os.replace(svg.with_suffix(suffix), target)
                # d2 writes its output private (0600); images are for everyone.
                target.chmod(IMAGE_MODE)
            if linked == "svg":
                (image_dir / f"{name}.png").unlink(missing_ok=True)
    _remove_stale_files(image_dir, stem, set(names))
    _remove_renamed_files(image_dir, path, items, set(names))

    for item, name, linked in zip(
        reversed(items), reversed(names), reversed(formats), strict=True
    ):
        alt = _nearest_heading(text, item.start()) or "Diagram"
        data = None if link else (image_dir / f"{name}.{linked}").read_bytes()
        text = text[: item.start()] + _embed(alt, name, linked, data) + text[item.end() :]
    write_document(path, text, overwrite=True)
    return [image_dir / f"{name}.{fmt}" for name, fmt in zip(names, formats, strict=True)]


def diagram_warnings(source: str, light: bool = False) -> list[str]:
    """Everything worth fixing in a D2 diagram: styles, crowded arrows, long labels.

    Args:
        source: The D2 source.
        light: The images are light only (``--light``): white fills are fine then.

    Returns:
        One message per problem (empty when there is none).
    """
    return dark_mode_warnings(source, light) + class_warnings(source) + crowding_warnings(source)


def class_warnings(source: str) -> list[str]:
    """Warn about ``shape: class`` with its own fill.

    D2 colours a class body with the stroke and puts white text on it, so a custom fill
    makes it unreadable; an ``|md`` rectangle draws a class as intended (models.md).

    Args:
        source: The D2 source.

    Returns:
        One message per class shape with a fill.
    """
    warnings = []
    for match in re.finditer(r"\bshape: *class\b", source):
        if re.search(r"\bfill:", _enclosing_map(source, match.start())):
            warnings.append(f"{_key(source, match.start())}: shape: class with a fill gets "
                            "white text on the stroke colour; use an |md rectangle for "
                            "classes, see models.md")
    return warnings


def crowding_warnings(source: str) -> list[str]:
    """Warn about figures whose arrows get hard to follow.

    More than :data:`MAX_ARROWS` arrows, two arrows between the same two shapes (one
    arrow with a combined label reads better), or an arrow label of more than
    :data:`MAX_LABEL_WORDS` words or with a line break.

    Args:
        source: The D2 source.

    Returns:
        One message per problem.
    """
    body = _LEGEND.sub("", source)
    warnings = label_warnings(body)
    if "sequence_diagram" in body:
        return warnings  # a sequence diagram's arrows are its messages, in order
    pairs = [(a, b) for a, _, b in _ARROW.findall(body)]
    if len(pairs) > MAX_ARROWS:
        warnings.append(f"{len(pairs)} arrows (more than {MAX_ARROWS}) are hard to follow; "
                        "split the figure or combine arrows, but keep the context's actors")
    seen: dict[frozenset[str], int] = {}
    for a, b in pairs:
        seen[frozenset((a, b))] = seen.get(frozenset((a, b)), 0) + 1
    for pair, count in seen.items():
        if count > 1 and len(pair) == 2:
            a, b = sorted(pair)
            warnings.append(f"{count} arrows between `{a}` and `{b}`; draw one with a "
                            "combined label")
    return warnings


def label_warnings(source: str) -> list[str]:
    """Warn about arrow labels that are too long or span lines.

    Args:
        source: The D2 source.

    Returns:
        One message per arrow whose label has more than :data:`MAX_LABEL_WORDS` words
        (a ``[protocol]`` part counts as one) or a ``\\n``.
    """
    warnings = []
    for match in _LABEL.finditer(source):
        label = match.group("label").strip().strip('"').strip()
        if not label:
            continue
        words = len(re.sub(r"\[[^\]]*\]", "P", label.replace("\\n", " ")).split())
        if words > MAX_LABEL_WORDS or "\\n" in label:
            warnings.append(f"label `{label}` has {words} words; keep arrow labels to "
                            f"{MAX_LABEL_WORDS} words, protocol in brackets, one line")
    return warnings


def dark_mode_warnings(source: str, light: bool = False) -> list[str]:
    """Find styles in a D2 diagram that break when the image shows in dark mode.

    The images carry a dark theme; fixed colours do not follow it. Warned about: a fixed
    ``font-color`` without a fill (dark text on the dark background), a white fill (a
    white box whose labels turn light), and a ``sequence_diagram`` in a labelled
    container (its key shows as a heading). With ``light`` the white fill is fine:
    light-only images may use draw.io colours on white.

    Args:
        source: The D2 source.
        light: The images are light only (``kingmadoc render --light``).

    Returns:
        One message per problem (empty when there is none).
    """
    warnings = []
    for match in re.finditer(r"\bfont-color: *[^;}\n]+", source):
        block = _enclosing_map(source, match.start())
        fill = re.search(r"\bfill: *\"?([^;}\n\"]+)", block)
        if not fill or fill.group(1).strip() == "transparent":
            warnings.append(f"{_key(source, match.start())}: font-color without a fill stays "
                            "dark on the dark background; remove the font-color (dark mode)")
    whites = [] if light else re.finditer(r"\bfill: *\"?(?:#fff\b|#ffffff|white)\"?", source, re.I)
    for match in whites:
        warnings.append(f"{_key(source, match.start())}: a white fill stays white while the "
                        "text on it turns light; use fill: transparent (dark mode)")
    for match in re.finditer(r"^( +)shape: *sequence_diagram", source, re.M):
        opening = source[: match.start()].rstrip().rsplit("\n", 1)[-1]
        if not re.search(r':\s*""\s*\{$', opening):
            warnings.append(f"{_key(source, match.start())}: a sequence_diagram in a labelled "
                            "container shows its key as a heading; label it \"\" or move it up")
    return warnings


def _enclosing_map(source: str, position: int) -> str:
    """The innermost ``{...}`` around ``position``."""
    depth, start = 0, position
    while start > 0:
        start -= 1
        if source[start] == "}":
            depth += 1
        elif source[start] == "{":
            if depth == 0:
                break
            depth -= 1
    depth, end = 0, position
    while end < len(source):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            if depth == 0:
                break
            depth -= 1
        end += 1
    return source[start : end + 1]


def _key(source: str, position: int) -> str:
    """The shape a style belongs to: the key on its line, else the enclosing map's key."""
    line = source[source.rfind("\n", 0, position) + 1 : position]
    key = re.match(r"\s*([\w.-]+)\s*:", line)
    if key and key.group(1) not in ("style", "shape"):
        return f"`{key.group(1)}`"
    opening = source[: source.rfind("{", 0, position)].rsplit("\n", 1)[-1]
    key = re.match(r"\s*([\w.-]+)\s*:", opening)
    return f"`{key.group(1)}`" if key else "a shape"


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
        # No shell; the program is the D2 binary from ensure_d2, the rest are file paths.
        result = subprocess.run(  # noqa: S603
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


def _layout_args(source: str) -> list[str]:
    """ELK unless the diagram picks its own engine (``vars: {d2-config: {layout-engine}}``).

    ELK routes arrows orthogonally, with fewer crossings than D2's default (dagre, curved
    splines that run over each other in bigger diagrams).
    """
    return [] if "layout-engine" in source else ["--layout", LAYOUT_ENGINE]


def _theme_args(dark: bool) -> list[str]:
    return ["--dark-theme", str(D2_DARK_THEME)] if dark else []


def _embed(alt: str, name: str, image_format: str, data: bytes | None = None) -> str:
    """The comment pointing at the source, and the image: embedded, or linked (no data)."""
    alt = alt.replace("[", "(").replace("]", ")")
    target = f"img/{name}.{image_format}"
    if data is not None:
        encoded = base64.b64encode(data).decode("ascii")
        target = f"data:{_MEDIA_TYPES[image_format]};base64,{encoded}"
    return f"<!-- kingmadoc:diagram img/{name}.d2 -->\n![{alt}]({target})"


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
        for suffix in (".svg", ".png", ".d2"):
            (image_dir / f"{name}{suffix}").unlink(missing_ok=True)


def _remove_stale_files(image_dir: Path, stem: str, keep: set[str]) -> None:
    """Delete images and sources of this document's diagrams that no longer exist."""
    pattern = re.compile(rf"({re.escape(stem)}-\d+)\.(svg|png|d2)")
    for file in image_dir.iterdir():
        match = pattern.fullmatch(file.name)
        if match and match.group(1) not in keep:
            file.unlink()
