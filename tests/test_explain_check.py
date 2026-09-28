"""``kingmadoc explain check``: an explainer is only done with its pictures shown."""

from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.explain import check_explainer

PNG = b"\x89PNG\r\n\x1a\n"


def _folder(tmp_path: Path, text: str, images: tuple[str, ...] = ("figure-1.png",)) -> Path:
    folder = tmp_path / "docs" / "explain" / "0001-shop"
    (folder / "img").mkdir(parents=True)
    for image in images:
        (folder / "img" / image).write_bytes(PNG)
    (folder / "README.md").write_text(text, encoding="utf-8")
    return folder


DONE = ("# Shop\n\n<!-- kingmadoc:diagram img/figure-1.d2 -->\n![Context](img/figure-1.png)\n\n"
        "**Figure 1.** Who uses it.\n\n<details><summary>More</summary>x</details>\n")


def test_a_finished_explainer_passes(tmp_path: Path) -> None:
    assert check_explainer(_folder(tmp_path, DONE)) == []


def test_every_way_to_end_up_without_pictures_is_caught(tmp_path: Path) -> None:
    """Nothing written, unrendered D2, missing images, captions without pictures, TODOs."""
    assert check_explainer(tmp_path) == [f"{tmp_path}: no explainer documents (README.md) yet"]
    cases = {
        "": "README.md: empty",
        "# S\n\n```d2\na -> b\n```\n\n**Figure 1.** x\n": "D2 source not rendered",
        "# S\n\n![x](img/figure-9.png)\n\n**Figure 1.** x\n": "missing images: img/figure-9.png",
        "# S\n\n**Figure 1.** x\n": "has figure captions but shows no pictures",
        DONE + "\n<one line: what it is>\n":
            "1 placeholders not filled in: <one line: what it is>",
    }
    for index, (text, problem) in enumerate(cases.items()):
        folder = _folder(tmp_path / str(index), text)
        problems = check_explainer(folder)
        assert any(problem in p for p in problems), (text, problems)


def test_split_checks_every_document(tmp_path: Path) -> None:
    folder = _folder(tmp_path, "# Shop\n\n| [Functional design](functional.md) | … |\n")
    (folder / "functional.md").write_text(DONE, encoding="utf-8")
    (folder / "technical.md").write_text("# T\n\n```d2\nx\n```\n**Figure 1.** y\n",
                                         encoding="utf-8")

    assert check_explainer(folder) == [
        "technical.md: D2 source not rendered (run kingmadoc render)",
        "technical.md: has figure captions but shows no pictures",
    ]


def test_cli_fails_until_finished(tmp_path: Path) -> None:
    folder = _folder(tmp_path, "# S\n\n```d2\na\n```\n**Figure 1.** x\n")

    failed = CliRunner().invoke(cli, ["explain", "check", str(folder)])
    assert failed.exit_code == 1 and "D2 source not rendered" in failed.output

    (folder / "README.md").write_text(DONE, encoding="utf-8")
    passed = CliRunner().invoke(cli, ["explain", "check", str(folder)])
    assert passed.exit_code == 0 and "finished (1 pictures)" in passed.output


def test_code_links_and_html_are_not_placeholders(tmp_path: Path) -> None:
    """Only real `<placeholders>` fail: never generics in code spans, links or HTML."""
    text = DONE + (
        "\nThe `OrderService` returns `List<Order>` and `Task<IActionResult>`.\n"
        "See <https://arc42.org> or <team@example.com>. <kbd>Ctrl</kbd>\n"
    )
    assert check_explainer(_folder(tmp_path, text)) == []
