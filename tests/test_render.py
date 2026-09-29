"""Tests for `kingmadoc render`: D2 diagrams in Markdown become SVG images (roadmap WP11)."""

import base64
import errno
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.exceptions import RenderError
from kingmadoc.render import render_file

# Stand-in for the d2 binary: "d2 [--pad N] in.d2 out.svg" writes a valid SVG with the
# source in a comment (so it can be turned into a PNG). Fails on sources containing BAD.
FAKE_D2 = """\
import sys
import tempfile
source, target = sys.argv[-2], sys.argv[-1]
text = open(source, encoding="utf-8").read()
if "BAD" in text:
    sys.stderr.write("err: failed to compile: connection missing destination\\n")
    sys.exit(1)
open(target, "w", encoding="utf-8").write(
    '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><!--'
    + text.strip() + "--></svg>"
)
import os
os.chmod(target, 0o600)  # like the real d2: the output is private
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
    """Each D2 block becomes a PNG (embedded) and an SVG; the document keeps only the image."""
    doc = _doc(tmp_path)

    images = render_file(doc, d2)

    img = doc.parent / "img"
    assert images == [img / "shop-1.png", img / "shop-2.png"]
    assert (img / "shop-1.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert "browser -> api: POST" in (img / "shop-1.svg").read_text(encoding="utf-8")
    assert (img / "shop-1.d2").read_text(encoding="utf-8") == "browser -> api: POST\n"
    text = doc.read_text(encoding="utf-8")
    png = base64.b64encode((img / "shop-1.png").read_bytes()).decode()
    assert f"![Overview](data:image/png;base64,{png})" in text
    assert "![How it works](data:image/png;base64," in text
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
        "shop-1.d2", "shop-1.png", "shop-1.svg", "shop-2.d2", "shop-2.png", "shop-2.svg",
    ]


def test_edited_source_updates_the_image(tmp_path: Path, d2: list[str]) -> None:
    """Editing the diagram's .d2 file and rendering again refreshes the image."""
    doc = _doc(tmp_path)
    render_file(doc, d2)
    (doc.parent / "img" / "shop-2.d2").write_text("api -> db: upsert\n", encoding="utf-8")

    render_file(doc, d2)

    assert "api -> db: upsert" in (doc.parent / "img" / "shop-2.svg").read_text("utf-8")


def test_removed_diagram_removes_its_image(tmp_path: Path, d2: list[str]) -> None:
    """Images of diagrams that no longer exist are deleted."""
    doc = _doc(tmp_path)
    render_file(doc, d2)

    doc.write_text("# Explainer\n\n```d2\nx -> y\n```\n", encoding="utf-8")
    render_file(doc, d2)

    assert sorted(p.name for p in (doc.parent / "img").iterdir()) == [
        "shop-1.d2", "shop-1.png", "shop-1.svg",
    ]


def test_svg_format_links_the_svg(tmp_path: Path, d2: list[str]) -> None:
    """--format svg: the document links the SVG (it follows dark mode) and no PNG is kept."""
    doc = _doc(tmp_path)
    render_file(doc, d2)

    images = render_file(doc, d2, image_format="svg", link=True)

    assert [p.name for p in images] == ["shop-1.svg", "shop-2.svg"]
    assert "![Overview](img/shop-1.svg)" in doc.read_text(encoding="utf-8")
    assert not list((doc.parent / "img").glob("*.png"))


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
    """KINGMADOC_D2 points at the binary; one short line per document (agents read it)."""
    doc = _doc(tmp_path)
    wrapper = _wrapper(tmp_path, d2)

    result = CliRunner().invoke(cli, ["render", str(doc)], env={"KINGMADOC_D2": str(wrapper)})

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [f"{doc}: 2 images (img/shop-1.png … img/shop-2.png)"]


def test_cli_render_verbose_lists_every_image(tmp_path: Path, d2: list[str]) -> None:
    """--verbose prints each image path, as before."""
    doc = _doc(tmp_path)

    result = CliRunner().invoke(
        cli, ["render", "--verbose", str(doc)], env={"KINGMADOC_D2": str(_wrapper(tmp_path, d2))}
    )

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        str(doc.parent / "img" / "shop-1.png"),
        str(doc.parent / "img" / "shop-2.png"),
    ]


@pytest.mark.skipif(
    not (os.environ.get("D2_BIN") or shutil.which("d2")), reason="d2 not available"
)
def test_real_d2_produces_pictures(tmp_path: Path) -> None:
    """With the real d2 binary: a PNG per diagram, embedded, with a valid SVG next to it."""
    doc = _doc(tmp_path)

    images = render_file(doc, [os.environ.get("D2_BIN") or shutil.which("d2") or "d2"])

    assert len(images) == 2
    text = doc.read_text(encoding="utf-8")
    assert "```d2" not in text
    for image in images:
        assert image.suffix == ".png" and image.read_bytes().startswith(b"\x89PNG")
        assert base64.b64encode(image.read_bytes()).decode() in text
        assert "<svg" in image.with_suffix(".svg").read_text(encoding="utf-8")[:500]


def test_older_folded_source_format_is_converted(tmp_path: Path, d2: list[str]) -> None:
    """Explainers rendered with the earlier <details> format lose the folded source."""
    old = (
        "# Doc\n\n## Data\n\n<!-- kingmadoc:render -->\n![Data](img/shop-1.svg)\n\n"
        "<details>\n<summary>Diagram source (D2)</summary>\n\n```d2\nuser -> order\n```\n\n"
        "</details>\n<!-- /kingmadoc:render -->\n"
    )
    doc = _doc(tmp_path, old)

    render_file(doc, d2, link=True)

    text = doc.read_text(encoding="utf-8")
    assert "<details>" not in text and "```d2" not in text
    assert "![Data](img/shop-1.png)" in text
    assert (doc.parent / "img" / "shop-1.d2").read_text(encoding="utf-8") == "user -> order\n"


def test_missing_source_file_is_an_error(tmp_path: Path, d2: list[str]) -> None:
    """A diagram reference without its .d2 file says which file is missing."""
    doc = _doc(tmp_path)
    render_file(doc, d2)
    (doc.parent / "img" / "shop-2.d2").unlink()

    with pytest.raises(RenderError, match="shop-2.d2"):
        render_file(doc, d2)


def test_readme_explainer_images_are_named_figure(tmp_path: Path, d2: list[str]) -> None:
    """An explainer folder's README.md gets img/figure-<n>.png, not img/README-<n>.png."""
    doc = tmp_path / "docs" / "explain" / "0001-shop" / "README.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(DOC, encoding="utf-8")

    images = render_file(doc, d2, link=True)

    assert [p.name for p in images] == ["figure-1.png", "figure-2.png"]
    assert "![Overview](img/figure-1.png)" in doc.read_text(encoding="utf-8")


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


def test_works_when_the_temp_dir_is_on_another_disk(
    tmp_path: Path, d2: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """os.replace cannot cross filesystems (EXDEV), so rendering stays next to the doc."""
    doc = _doc(tmp_path)
    other_disk = tmp_path / "other-disk"
    other_disk.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(other_disk))
    real_replace = os.replace

    def replace(src: str | Path, dst: str | Path) -> None:
        if Path(src).is_relative_to(other_disk) != Path(dst).is_relative_to(other_disk):
            raise OSError(errno.EXDEV, "Invalid cross-device link")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", replace)

    images = render_file(doc, d2)

    assert [p.name for p in images] == ["shop-1.png", "shop-2.png"]
    assert sorted(p.name for p in doc.parent.iterdir()) == ["img", "shop.md"]  # no leftovers


def test_readme_and_index_in_one_folder_keep_their_own_images(
    tmp_path: Path, d2: list[str]
) -> None:
    """Outside explainer folders images keep the document's name, so they never collide."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text(DOC, encoding="utf-8")
    (docs / "README.md").write_text("# Readme\n\n```d2\nx -> y\n```\n", encoding="utf-8")

    render_file(docs / "index.md", d2)
    render_file(docs / "README.md", d2)

    names = sorted(p.name for p in (docs / "img").iterdir())
    assert names == [
        "README-1.d2", "README-1.png", "README-1.svg", "index-1.d2", "index-1.png",
        "index-1.svg", "index-2.d2", "index-2.png", "index-2.svg",
    ]


def test_images_under_an_old_name_are_removed(tmp_path: Path, d2: list[str]) -> None:
    """An explainer rendered as img/README-<n> before moves to figure-<n> without leftovers."""
    folder = tmp_path / "docs" / "explain" / "0001-shop"
    (folder / "img").mkdir(parents=True)
    (folder / "img" / "README-1.d2").write_text("a -> b\n", encoding="utf-8")
    (folder / "img" / "README-1.svg").write_text("<svg/>", encoding="utf-8")
    (folder / "README.md").write_text(
        "# Shop\n\n<!-- kingmadoc:diagram img/README-1.d2 -->\n![Shop](img/README-1.svg)\n",
        encoding="utf-8",
    )

    render_file(folder / "README.md", d2)

    assert sorted(p.name for p in (folder / "img").iterdir()) == [
        "figure-1.d2", "figure-1.png", "figure-1.svg",
    ]
    assert (folder / "img" / "figure-1.d2").read_text(encoding="utf-8") == "a -> b\n"


def _commands(tmp_path: Path, d2: list[str], monkeypatch: pytest.MonkeyPatch, **kw: bool) -> list:
    import subprocess

    from kingmadoc import render

    seen: list[list[str]] = []
    real_run = subprocess.run

    def run(command: list[str], **kwargs: object):  # type: ignore[no-untyped-def]
        seen.append(command)
        return real_run(command, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(render.subprocess, "run", run)
    render_file(_doc(tmp_path), d2, **kw)
    return seen


def test_images_follow_the_viewers_dark_theme(
    tmp_path: Path, d2: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every image gets D2's dark theme too, shown when the viewer uses dark mode."""
    commands = _commands(tmp_path, d2, monkeypatch)

    assert commands and all("--dark-theme" in c for c in commands)


def test_light_renders_without_a_dark_theme(
    tmp_path: Path, d2: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """render --light keeps the images light, whatever the viewer's theme."""
    commands = _commands(tmp_path, d2, monkeypatch, dark=False)

    assert commands and not any("--dark-theme" in c for c in commands)


def test_cli_light_option(tmp_path: Path, d2: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """`kingmadoc render --light` passes dark=False."""
    from kingmadoc import cli as cli_module

    calls: list[bool] = []
    monkeypatch.setattr(
        cli_module,
        "render_file",
        lambda path, cmd, dark=True, **_: calls.append(dark) or [],
    )
    doc = _doc(tmp_path)

    result = CliRunner().invoke(
        cli, ["render", "--light", str(doc)], env={"KINGMADOC_D2": str(_wrapper(tmp_path, d2))}
    )

    assert result.exit_code == 0, result.output
    assert calls == [False]


def test_dark_mode_problems_are_reported() -> None:
    """render warns about styles that break in dark mode (it does not change the source)."""
    from kingmadoc.render import dark_mode_warnings

    source = (
        'title: "T" {shape: text; style: {bold: true; font-color: "#000000"}}\n'
        'b: "Boundary" {style: {fill: "#ffffff"; stroke: "#444"}}\n'
        'seq: {\n  shape: sequence_diagram\n}\n'
        'ok: "Box" {style: {fill: "#438dd5"; font-color: "#ffffff"}}\n'
        'see: "Through" {style: {fill: transparent}}\n'
    )

    warnings = dark_mode_warnings(source)

    assert len(warnings) == 3, warnings
    assert any("font-color" in w and "title" in w for w in warnings)
    assert any("white" in w for w in warnings)
    assert any("sequence_diagram" in w and "seq" in w for w in warnings)


def test_cli_render_prints_the_dark_mode_warnings(tmp_path: Path, d2: list[str]) -> None:
    """The warning names the figure, so the agent knows which .d2 file to fix."""
    doc = _doc(tmp_path, '# T\n\n```d2\nt: "T" {style: {font-color: "#000000"}}\n```\n')

    env = {"KINGMADOC_D2": str(_wrapper(tmp_path, d2))}
    result = CliRunner().invoke(cli, ["render", "--format", "svg", str(doc)], env=env)

    assert result.exit_code == 0, result.output
    assert "shop-1.d2" in result.stderr and "dark mode" in result.stderr


def test_rendering_an_explainer_points_at_the_preview(tmp_path: Path, d2: list[str]) -> None:
    """While VS Code would open explainers as text, render says how to see the pictures."""
    doc = tmp_path / "docs" / "explain" / "0001-shop" / "README.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(DOC, encoding="utf-8")

    result = CliRunner().invoke(
        cli, ["render", str(doc)], env={"KINGMADOC_D2": str(_wrapper(tmp_path, d2))}
    )

    assert result.exit_code == 0, result.output
    assert "Ctrl+Shift+V" in result.stderr and "--vscode" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_images_are_readable_by_everyone(tmp_path: Path, d2: list[str]) -> None:
    """Images come out of a private temp dir; they get normal file modes (0644)."""
    images = render_file(_doc(tmp_path), d2)

    assert all(p.stat().st_mode & 0o777 == 0o644 for p in images)


def test_images_use_the_elk_layout(
    tmp_path: Path, d2: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """ELK routes arrows straight and at right angles (dagre curves them over each other)."""
    commands = _commands(tmp_path, d2, monkeypatch)

    assert commands and all(c[c.index("--layout") + 1] == "elk" for c in commands)


def test_a_diagram_that_picks_its_layout_keeps_it(
    tmp_path: Path, d2: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """vars.d2-config.layout-engine in the source wins over the default."""
    import subprocess

    from kingmadoc import render

    seen: list[list[str]] = []
    real_run = subprocess.run

    def run(command: list[str], **kwargs: object):  # type: ignore[no-untyped-def]
        seen.append(command)
        return real_run(command, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(render.subprocess, "run", run)
    source = "vars: {d2-config: {layout-engine: dagre}}\na -> b\n"
    render_file(_doc(tmp_path, f"# T\n\n```d2\n{source}```\n"), d2)

    assert seen and "--layout" not in seen[0]


def test_crowded_diagrams_are_reported() -> None:
    """More than 12 arrows, or two arrows between the same pair, make a figure hard to read."""
    from kingmadoc.render import diagram_warnings

    crowded = "\n".join(f"a{i} -> b{i}: x" for i in range(13))
    twice = "api -> db: reads\ndb -> api: rows\nweb -> api: calls\n"

    assert any("13 arrows" in w for w in diagram_warnings(crowded))
    assert any("`api` and `db`" in w for w in diagram_warnings(twice))
    assert diagram_warnings("a -> b: x\nb -> c: y\n") == []


def test_cli_format_svg_and_the_dark_mode_warnings(tmp_path: Path, d2: list[str]) -> None:
    """PNG (default) is light, so dark-mode warnings only matter with --format svg."""
    doc = _doc(tmp_path, '# T\n\n```d2\nt: "T" {style: {font-color: "#000000"}}\n```\n')
    env = {"KINGMADOC_D2": str(_wrapper(tmp_path, d2))}

    png = CliRunner().invoke(cli, ["render", str(doc)], env=env)
    svg = CliRunner().invoke(cli, ["render", "--format", "svg", "--link", str(doc)], env=env)

    assert png.exit_code == 0 and "dark mode" not in png.stderr, png.output
    assert svg.exit_code == 0 and "dark mode" in svg.stderr, svg.output
    assert "![T](img/shop-1.svg)" in doc.read_text(encoding="utf-8")


def test_a_failing_png_falls_back_to_svg(
    tmp_path: Path, d2: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A PNG error (a missing resvg wheel, a Rust panic) never leaves a document without
    pictures: that diagram links its SVG instead."""
    from kingmadoc import render
    from kingmadoc.exceptions import RenderError

    def broken(_svg: str) -> bytes:
        raise RenderError("resvg panicked")

    monkeypatch.setattr(render, "svg_to_png", broken)
    doc = _doc(tmp_path)

    images = render_file(doc, d2)

    text = doc.read_text(encoding="utf-8")
    assert images and all(i.suffix == ".svg" and i.is_file() for i in images)
    assert "```d2" not in text
    assert text.count("](data:image/svg+xml;base64,") == len(images)


def test_the_cli_starts_without_resvg() -> None:
    """resvg-py is imported only when a PNG is made: every other command still works."""
    import subprocess
    import sys

    code = (
        "import sys; sys.modules['resvg_py'] = None\n"  # import resvg_py -> ImportError
        "from kingmadoc.cli import cli\n"
        "from kingmadoc.exceptions import RenderError\n"
        "from kingmadoc.raster import svg_to_png\n"
        "try:\n"
        "    svg_to_png('<svg xmlns=\"http://www.w3.org/2000/svg\"/>')\n"
        "except RenderError as exc:\n"
        "    print('render error:', exc)\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,  # noqa: S603
                          check=False)

    assert done.returncode == 0, done.stderr
    assert "render error: PNG conversion is not available here" in done.stdout


def test_one_broken_document_does_not_cost_the_others_their_pictures(
    tmp_path: Path, d2: list[str]
) -> None:
    """render renders every document; the broken one stays unchanged and fails the run."""
    good = _doc(tmp_path)
    broken = good.parent / "technical.md"
    broken.write_text("# T\n\n```d2\nBAD\n```\n", encoding="utf-8")
    wrapper = _wrapper(tmp_path, d2)

    result = CliRunner().invoke(cli, ["render", str(broken), str(good)],
                                env={"KINGMADOC_D2": str(wrapper)})

    assert result.exit_code == 1
    assert "1 document not rendered" in result.output
    assert "```d2" not in good.read_text(encoding="utf-8")  # rendered after the failure
    assert "```d2\nBAD" in broken.read_text(encoding="utf-8")  # untouched, to fix


def test_embedding_is_the_default_and_link_links(tmp_path: Path, d2: list[str]) -> None:
    """The image is a data URI by default; --link writes the relative link; both keep img/."""
    doc = _doc(tmp_path)
    env = {"KINGMADOC_D2": str(_wrapper(tmp_path, d2))}

    CliRunner().invoke(cli, ["render", "--link", str(doc)], env=env)
    linked = doc.read_text(encoding="utf-8")
    CliRunner().invoke(cli, ["render", str(doc)], env=env)  # converts the relative links
    embedded = doc.read_text(encoding="utf-8")

    assert "![Overview](img/shop-1.png)" in linked
    assert "](img/" not in embedded and embedded.count("](data:image/png;base64,") == 2
    assert all((doc.parent / "img" / f"shop-1.{s}").is_file() for s in ("d2", "svg", "png"))


def test_rendering_an_embedded_document_again_replaces_the_image(
    tmp_path: Path, d2: list[str]
) -> None:
    """A second render replaces the data URI under the same comment; it never duplicates."""
    doc = _doc(tmp_path)
    render_file(doc, d2)
    first = doc.read_text(encoding="utf-8")

    render_file(doc, d2)

    text = doc.read_text(encoding="utf-8")
    assert text == first
    assert text.count("<!-- kingmadoc:diagram img/shop-1.d2 -->") == 1
    assert text.count("data:image/png;base64,") == 2


def test_long_and_multiline_arrow_labels_are_warned_about() -> None:
    """More than four words (a [protocol] counts as one) or a line break in a label."""
    from kingmadoc.render import MAX_LABEL_WORDS, crowding_warnings

    source = (
        'a -> b: "sends the whole order to it"\n'
        "c -> d: first\\nsecond\n"
        'e -> f: "reads orders [JSON/HTTPS]"\n'
        "g -> h\n"
    )
    warnings = crowding_warnings(source)

    assert MAX_LABEL_WORDS == 4
    assert len(warnings) == 2
    assert "`sends the whole order to it` has 6 words" in warnings[0]
    assert "keep arrow labels to 4 words, protocol in brackets, one line" in warnings[0]
    assert "first\\nsecond" in warnings[1]


def test_class_shape_with_a_fill_is_warned_about() -> None:
    """D2 puts white text on a class body coloured with the stroke; use an |md rectangle."""
    from kingmadoc.render import diagram_warnings

    warnings = diagram_warnings('Order: {shape: class; style: {fill: "#dae8fc"}}\n')
    plain = diagram_warnings("Order: {shape: class}\n")

    assert any("use an |md rectangle for classes, see models.md" in w for w in warnings)
    assert not any("|md" in w for w in plain)


def test_light_images_allow_white_fills() -> None:
    """--light: draw.io colours on white are wanted, so a white fill is no problem."""
    from kingmadoc.render import dark_mode_warnings

    source = 'a: A {style: {fill: "#ffffff"}}\n'

    assert any("white fill" in w for w in dark_mode_warnings(source))
    assert dark_mode_warnings(source, light=True) == []
