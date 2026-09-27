"""Tests for SVG -> PNG: every Markdown viewer shows a PNG, and the text must survive."""

import base64
import re
import struct
from pathlib import Path

import pytest

from kingmadoc.exceptions import RenderError
from kingmadoc.raster import ZOOM, font_family, svg_to_png, woff_to_sfnt

# A real D2 SVG (title, a markdown label, an italic edge label; dark theme included).
SAMPLE = (Path(__file__).parent / "data" / "d2-sample.svg").read_text(encoding="utf-8")


def _png_size(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    return width, height


def _dark_pixels(png: bytes) -> int:
    """Count near-black pixels: the text (and nothing else in the sample is that dark)."""
    import zlib

    width, height = _png_size(png)
    data, pos = b"", 8
    color_type = png[25]
    while pos < len(png):
        length, kind = struct.unpack(">I4s", png[pos : pos + 8])
        if kind == b"IDAT":
            data += png[pos + 8 : pos + 8 + length]
        pos += 12 + length
    raw = zlib.decompress(data)
    channels = 4 if color_type == 6 else 3
    stride = width * channels + 1
    dark, prev = 0, bytearray(stride - 1)
    for y in range(height):
        line = raw[y * stride : (y + 1) * stride]
        kind, row = line[0], bytearray(line[1:])
        for x in range(len(row)):
            a = row[x - channels] if x >= channels else 0
            b, c = prev[x], prev[x - channels] if x >= channels else 0
            if kind == 1:
                row[x] = (row[x] + a) & 255
            elif kind == 2:
                row[x] = (row[x] + b) & 255
            elif kind == 3:
                row[x] = (row[x] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[x] = (row[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        dark += sum(
            1 for x in range(0, len(row), channels)
            if max(row[x : x + 3]) < 80 and (channels == 3 or row[x + 3] > 200)
        )
        prev = row
    return dark


def test_png_is_twice_the_svg_size() -> None:
    """Sharp on high-DPI screens."""
    width = int(re.search(r'viewBox="0 0 (\d+) (\d+)"', SAMPLE).group(1))  # type: ignore[union-attr]

    png = svg_to_png(SAMPLE)

    assert _png_size(png)[0] == width * ZOOM


def test_the_text_is_drawn_with_the_embedded_fonts() -> None:
    """resvg reads no WOFF: without the unpacked fonts (and no system fonts) there is no
    text at all. With them, the title, labels and descriptions add many dark pixels."""
    import resvg_py

    no_text = bytes(resvg_py.svg_to_bytes(svg_string=SAMPLE, skip_system_fonts=True, zoom=ZOOM))

    assert _dark_pixels(svg_to_png(SAMPLE)) > _dark_pixels(no_text) + 1000


def test_woff_unpacks_to_the_source_sans_font() -> None:
    """D2 embeds Source Sans Pro as WOFF; unpacked, its name table says so."""
    data = re.search(r"font-woff;base64,([A-Za-z0-9+/=]+)", SAMPLE).group(1)  # type: ignore[union-attr]

    sfnt = woff_to_sfnt(base64.b64decode(data))

    assert font_family(sfnt) == "Source Sans Pro"


def test_bad_input() -> None:
    """Not WOFF, or not SVG: a clear error."""
    with pytest.raises(RenderError, match="WOFF"):
        woff_to_sfnt(b"not a font")
    with pytest.raises(RenderError, match="PNG"):
        svg_to_png("<not svg")
