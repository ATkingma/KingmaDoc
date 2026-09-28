"""SVG to PNG for rendered diagrams, so every Markdown viewer shows them.

VS Code, Visual Studio, Rider, GitHub, GitLab and Bitbucket all show a PNG in Markdown;
several block or mishandle SVG. The conversion runs offline with resvg (a small wheel,
no system libraries). D2 embeds its fonts (Source Sans Pro, as WOFF subsets) in each
SVG; resvg cannot read WOFF or CSS ``@font-face``, so the fonts are unpacked to TrueType
and the CSS names D2 made up (``d2-123-font-bold``) become the real family and weight.
Without that, text is measured with another font and clipped.
"""

from __future__ import annotations

import base64
import re
import struct
import tempfile
import zlib
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from kingmadoc.exceptions import RenderError

# 2x: sharp on high-DPI screens, still small (a typical diagram is 100-300 KB).
ZOOM = 2
_FONT_FACE = re.compile(
    r"@font-face\s*\{\s*font-family:\s*(d2-\d+-font-[\w-]+);\s*"
    r"src:\s*url\(\"data:application/font-woff;base64,([A-Za-z0-9+/=]+)\"\)[^}]*\}"
)
_FONT_USE = re.compile(r"font-family:\s*\"?d2-\d+-font-([\w-]+)\"?")
_STYLES: Mapping[str, str] = MappingProxyType({
    "regular": "font-weight: normal; font-style: normal",
    "bold": "font-weight: bold; font-style: normal",
    "semibold": "font-weight: 600; font-style: normal",
    "italic": "font-weight: normal; font-style: italic",
})


def svg_to_png(svg: str) -> bytes:
    """Rasterize a D2 SVG with its own fonts.

    Args:
        svg: The SVG text D2 wrote.

    Returns:
        PNG bytes at :data:`ZOOM` times the SVG size (light theme: resvg ignores the
        dark-mode media query, so the picture reads on any background).

    Raises:
        RenderError: If the SVG cannot be rasterized.
    """
    faces = _FONT_FACE.findall(svg)
    families: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="kingmadoc-fonts-") as tmp:
        files = []
        for index, (name, data) in enumerate(faces):
            try:
                sfnt = woff_to_sfnt(base64.b64decode(data))
                families[name] = font_family(sfnt) or "sans-serif"
            except (RenderError, ValueError, struct.error, zlib.error):
                continue  # an unreadable font: its text falls back to another font
            path = Path(tmp) / f"{index}.ttf"
            path.write_bytes(sfnt)
            files.append(str(path))
        family = next(iter(families.values()), "sans-serif")
        text = _FONT_USE.sub(
            lambda m: f'font-family: "{family}"; {_STYLES.get(m.group(1), _STYLES["regular"])}',
            re.sub(r"@font-face\s*\{[^}]*\}", "", svg),
        )
        try:
            # Imported here: without a resvg wheel for this platform, only PNG is lost,
            # not every kingmadoc command.
            import resvg_py
        except ImportError as exc:
            raise RenderError(f"PNG conversion is not available here (resvg-py): {exc}") from exc
        try:
            png = resvg_py.svg_to_bytes(
                svg_string=text, font_files=files, skip_system_fonts=bool(files), zoom=ZOOM
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:  # noqa: BLE001 - resvg raises bare exceptions and Rust panics (BaseException)
            raise RenderError(f"Could not convert the diagram to PNG: {exc}") from exc
    return bytes(png)


def woff_to_sfnt(data: bytes) -> bytes:
    """Unpack a WOFF 1.0 font to the TrueType/OpenType file it wraps.

    Args:
        data: The WOFF file.

    Returns:
        The sfnt (``.ttf``/``.otf``) bytes.

    Raises:
        RenderError: If ``data`` is not WOFF 1.0.
    """
    if len(data) < 44 or data[:4] != b"wOFF":
        raise RenderError("not a WOFF 1.0 font")
    flavor, _length, count = struct.unpack(">4xIIH", data[:14])
    tables = []
    for i in range(count):
        tag, offset, size, original, checksum = struct.unpack(
            ">4sIIII", data[44 + 20 * i : 64 + 20 * i]
        )
        raw = data[offset : offset + size]
        tables.append((tag, zlib.decompress(raw) if size < original else raw, checksum))
    tables.sort()
    search = 1
    while search * 2 <= count:
        search *= 2
    header = struct.pack(
        ">IHHHH", flavor, count, search * 16, search.bit_length() - 1, count * 16 - search * 16
    )
    offset = 12 + 16 * count
    directory, body = b"", b""
    for tag, table, checksum in tables:
        directory += struct.pack(">4sIII", tag, checksum, offset + len(body), len(table))
        body += table + b"\0" * (-len(table) % 4)
    return header + directory + body


def font_family(sfnt: bytes) -> str:
    """Return a font's family name (name table, name ID 1), or "" when it has none.

    Args:
        sfnt: A TrueType/OpenType font.

    Returns:
        E.g. ``"Source Sans Pro"``.
    """
    count = struct.unpack(">H", sfnt[4:6])[0]
    for i in range(count):
        tag, _checksum, offset, length = struct.unpack(">4sIII", sfnt[12 + 16 * i : 28 + 16 * i])
        if tag != b"name":
            continue
        table = sfnt[offset : offset + length]
        _format, records, strings = struct.unpack(">HHH", table[:6])
        for j in range(records):
            platform, _enc, _lang, name_id, size, start = struct.unpack(
                ">HHHHHH", table[6 + 12 * j : 18 + 12 * j]
            )
            if name_id == 1:
                raw = table[strings + start : strings + start + size]
                return raw.decode("utf-16-be" if platform in (0, 3) else "latin-1", "replace")
    return ""
