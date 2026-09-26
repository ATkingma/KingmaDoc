"""Tests for `kingmadoc render`: D2 diagrams in Markdown become SVG images (roadmap WP11)."""

import os
import shutil
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.exceptions import RenderError
from kingmadoc.render import render_file

# Stand-in for the d2 binary: "d2 [--pad N] in.d2 out.svg". Fails on sources containing BAD.
FAKE_D2 = """\
import sys
source, target = sys.argv[-2], sys.argv[-1]
text = open(source, encoding="utf-8").read()
if "BAD" in text:
    sys.stderr.write("err: failed to compile: connection missing destination\\n")
    sys.exit(1)
open(target, "w", encoding="utf-8").write("<svg>" + text.strip() + "</svg>")
"""

DOC = """\
# Explainer

## Overview

```d2
browser -> api: POST
```

## How it works

Some text.

```mermaid
flowchart TD
  a --> b
```

```d2
api -> db: insert
```
"""


@pytest.fixture
def d2(tmp_path: Path) -> list[str]:
    script = tmp_path / "fake_d2.py"
    script.write_text(FAKE_D2, encoding="utf-8")
    return [sys.executable, str(script)]


def _doc(tmp_path: Path, text: str = DOC) -> Path:
    path = tmp_path / "docs" / "explain" / "shop.md"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_diagrams_become_images_and_their_source_moves_out(
    tmp_path: Path, d2: list[str]
) -> None:
    """Each D2 block becomes an SVG; the document keeps only the image (source in img/)."""
    doc = _doc(tmp_path)

    images = render_file(doc, d2)

    img = doc.parent / "img"
    assert images == [img / "shop-1.svg", img / "shop-2.svg"]
    assert (img / "shop-1.svg").read_text(encoding="utf-8") == "<svg>browser -> api: POST</svg>"
    assert (img / "shop-1.d2").read_text(encoding="utf-8") == "browser -> api: POST\n"
    text = doc.read_text(encoding="utf-8")
    assert "![Overview](img/shop-1.svg)" in text
    assert "![How it works](img/shop-2.svg)" in text
    assert "```d2" not in text and "<details>" not in text
    assert "<!-- kingmadoc:diagram img/shop-1.d2 -->" in text  # invisible in previews
    assert "```mermaid\nflowchart TD" in text  # other diagram languages are left alone


def test_rendering_twice_changes_nothing(tmp_path: Path, d2: list[str]) -> None:
    """Re-rendering is idempotent."""
    doc = _doc(tmp_path)
    render_file(doc, d2)
    first = doc.read_text(encoding="utf-8")

    render_file(doc, d2)

    assert doc.read_text(encoding="utf-8") == first
    assert sorted(p.name for p in (doc.parent / "img").iterdir()) == [
        "shop-1.d2", "shop-1.svg", "shop-2.d2", "shop-2.svg",
    ]


def test_edited_source_updates_the_image(tmp_path: Path, d2: list[str]) -> None:
    """Editing the diagram's .d2 file and rendering again refreshes the image."""
    doc = _doc(tmp_path)
    render_file(doc, d2)
    (doc.parent / "img" / "shop-2.d2").write_text("api -> db: upsert\n", encoding="utf-8")

    render_file(doc, d2)

    assert (doc.parent / "img" / "shop-2.svg").read_text(encoding="utf-8") == (
        "<svg>api -> db: upsert</svg>"
    )


def test_removed_diagram_removes_its_image(tmp_path: Path, d2: list[str]) -> None:
    """Images of diagrams that no longer exist are deleted."""
    doc = _doc(tmp_path)
    render_file(doc, d2)

    doc.write_text("# Explainer\n\n```d2\nx -> y\n```\n", encoding="utf-8")
    render_file(doc, d2)

    assert sorted(p.name for p in (doc.parent / "img").iterdir()) == ["shop-1.d2", "shop-1.svg"]


def test_a_broken_diagram_changes_nothing(tmp_path: Path, d2: list[str]) -> None:
    """If one diagram fails, the error says which, and no file is written or changed."""
    doc = _doc(tmp_path, DOC.replace("api -> db: insert", "BAD ->"))

    with pytest.raises(RenderError, match="diagram 2.*connection missing destination"):
        render_file(doc, d2)

    assert doc.read_text(encoding="utf-8") == DOC.replace("api -> db: insert", "BAD ->")
    assert not (doc.parent / "img").exists()


def test_document_without_d2_is_left_alone(tmp_path: Path, d2: list[str]) -> None:
    """No D2 blocks: nothing to do."""
    doc = _doc(tmp_path, "# Plain\n\n```mermaid\nflowchart TD\n```\n")

    assert render_file(doc, d2) == []
    assert not (doc.parent / "img").exists()


def test_cli_explains_how_to_install_d2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without D2, `render` fails with an install hint instead of a traceback."""
    doc = _doc(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("KINGMADOC_D2_DOWNLOAD", "0")  # no network in this test
    monkeypatch.setenv("KINGMADOC_CACHE_DIR", str(tmp_path / "cache"))  # not the real cache
    monkeypatch.delenv("KINGMADOC_D2", raising=False)

    result = CliRunner().invoke(cli, ["render", str(doc)])

    assert result.exit_code == 1
    assert "D2 is not installed" in result.output
    assert "d2lang.com" in result.output


def _wrapper(tmp_path: Path, d2: list[str]) -> Path:
    """An executable that runs the fake d2 (KINGMADOC_D2 takes a single path)."""
    wrapper = tmp_path / ("d2.bat" if os.name == "nt" else "d2")
    if os.name == "nt":
        wrapper.write_text(f'@"{d2[0]}" "{d2[1]}" %*\n', encoding="utf-8")
    else:
        wrapper.write_text(f'#!/bin/sh\nexec "{d2[0]}" "{d2[1]}" "$@"\n', encoding="utf-8")
        wrapper.chmod(0o755)
    return wrapper


def test_cli_renders_with_the_configured_binary(tmp_path: Path, d2: list[str]) -> None:
    """KINGMADOC_D2 points at the binary; the CLI prints the images it wrote."""
    doc = _doc(tmp_path)
    wrapper = _wrapper(tmp_path, d2)

    result = CliRunner().invoke(cli, ["render", str(doc)], env={"KINGMADOC_D2": str(wrapper)})

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        str(doc.parent / "img" / "shop-1.svg"),
        str(doc.parent / "img" / "shop-2.svg"),
    ]


@pytest.mark.skipif(
    not (os.environ.get("D2_BIN") or shutil.which("d2")), reason="d2 not available"
)
def test_real_d2_produces_svg(tmp_path: Path) -> None:
    """With the real d2 binary, the images are valid SVG."""
    doc = _doc(tmp_path)

    images = render_file(doc, [os.environ.get("D2_BIN") or shutil.which("d2") or "d2"])

    assert len(images) == 2
    for image in images:
        assert "<svg" in image.read_text(encoding="utf-8")[:500]


def test_older_folded_source_format_is_converted(tmp_path: Path, d2: list[str]) -> None:
    """Explainers rendered with the earlier <details> format lose the folded source."""
    old = (
        "# Doc\n\n## Data\n\n<!-- kingmadoc:render -->\n![Data](img/shop-1.svg)\n\n"
        "<details>\n<summary>Diagram source (D2)</summary>\n\n```d2\nuser -> order\n```\n\n"
        "</details>\n<!-- /kingmadoc:render -->\n"
    )
    doc = _doc(tmp_path, old)

    render_file(doc, d2)

    text = doc.read_text(encoding="utf-8")
    assert "<details>" not in text and "```d2" not in text
    assert "![Data](img/shop-1.svg)" in text
    assert (doc.parent / "img" / "shop-1.d2").read_text(encoding="utf-8") == "user -> order\n"


def test_missing_source_file_is_an_error(tmp_path: Path, d2: list[str]) -> None:
    """A diagram reference without its .d2 file says which file is missing."""
    doc = _doc(tmp_path)
    render_file(doc, d2)
    (doc.parent / "img" / "shop-2.d2").unlink()

    with pytest.raises(RenderError, match="shop-2.d2"):
        render_file(doc, d2)


def test_readme_explainer_images_are_named_figure(tmp_path: Path, d2: list[str]) -> None:
    """An explainer folder's README.md gets img/figure-<n>.svg, not img/README-<n>.svg."""
    doc = tmp_path / "docs" / "explain" / "0001-shop" / "README.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(DOC, encoding="utf-8")

    images = render_file(doc, d2)

    assert [p.name for p in images] == ["figure-1.svg", "figure-2.svg"]
    assert "![Overview](img/figure-1.svg)" in doc.read_text(encoding="utf-8")


def test_rendering_an_explainer_updates_the_index(tmp_path: Path, d2: list[str]) -> None:
    """After rendering docs/explain/<ID>-<name>/README.md, the index lists it by title."""
    doc = tmp_path / "docs" / "explain" / "0001-shop" / "README.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(DOC, encoding="utf-8")

    result = CliRunner().invoke(
        cli, ["render", str(doc)], env={"KINGMADOC_D2": str(_wrapper(tmp_path, d2))}
    )

    assert result.exit_code == 0, result.output
    index = (tmp_path / "docs" / "explain" / "README.md").read_text(encoding="utf-8")
    assert "[Explainer](0001-shop/README.md)" in index
