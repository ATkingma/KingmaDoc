"""Tests for explainer folders: `kingmadoc explain new` → docs/explain/<NNNN>-<slug>/."""

import re
from pathlib import Path

from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.explain import EXPLAIN_DIR, explainer_folder, index_markdown, read_entries

EXPLAINER = """\
# Contact form: architecture explained

| | |
| --- | --- |
| **Scope** | feature |
| **Stack** | Next.js |
| **Based on** | 29244f7 · 2026-09-26 · KingmaDoc skill explaining-code 4.1.0 (arc42) |
"""


def _new(root: Path, name: str) -> Result:
    return CliRunner().invoke(cli, ["explain", "new", name, "--root", str(root)])


def test_first_explainer_gets_id_0001(tmp_path: Path) -> None:
    """The folder is <NNNN>-<slug>; the command prints the README.md to write."""
    result = _new(tmp_path, "The contact form")

    assert result.exit_code == 0, result.output
    folder = tmp_path / EXPLAIN_DIR / "0001-the-contact-form"
    assert folder.is_dir()
    assert result.stdout.strip() == str(folder / "README.md")


def test_ids_count_up_and_are_never_reused(tmp_path: Path) -> None:
    """A new subject gets the highest ID + 1, also when a lower one was deleted."""
    (tmp_path / EXPLAIN_DIR / "0001-login").mkdir(parents=True)
    (tmp_path / EXPLAIN_DIR / "0004-payments").mkdir()

    folder, created = explainer_folder(tmp_path, "Search")

    assert created
    assert folder.name == "0005-search"


def test_the_same_subject_reuses_its_folder(tmp_path: Path) -> None:
    """Explaining a subject again updates its folder (by name or by ID), no duplicates."""
    first = _new(tmp_path, "Contact form")
    again = _new(tmp_path, "contact  FORM")
    by_id = _new(tmp_path, "1")

    assert first.stdout == again.stdout == by_id.stdout
    assert [p.name for p in (tmp_path / EXPLAIN_DIR).iterdir() if p.is_dir()] == [
        "0001-contact-form"
    ]


def test_index_lists_every_explainer(tmp_path: Path) -> None:
    """docs/explain/README.md: ID, linked name, scope and date, read from each explainer."""
    folder = tmp_path / EXPLAIN_DIR / "0001-contact-form"
    folder.mkdir(parents=True)
    (folder / "README.md").write_text(EXPLAINER, encoding="utf-8")
    (tmp_path / EXPLAIN_DIR / "0002-branch-feature-x").mkdir()

    text = re.sub(r" +", " ", index_markdown(read_entries(tmp_path / EXPLAIN_DIR)))

    assert "| 0001 | [Contact form](0001-contact-form/README.md) | feature | 2026-09-26 |" in text
    assert "| 0002 | [branch-feature-x](0002-branch-feature-x/) | | |" in text


def test_explain_new_writes_the_index(tmp_path: Path) -> None:
    """The index is kept up to date by `explain new` (and by `render`)."""
    assert _new(tmp_path, "Checkout").exit_code == 0

    index = (tmp_path / EXPLAIN_DIR / "README.md").read_text(encoding="utf-8")
    assert "0001" in index and "checkout" in index


def test_blank_name_is_refused(tmp_path: Path) -> None:
    """A subject needs a name."""
    result = _new(tmp_path, "  ")

    assert result.exit_code == 1
    assert not (tmp_path / EXPLAIN_DIR).exists()


def test_titles_with_table_characters_do_not_break_the_index(tmp_path: Path) -> None:
    """| and ] in a title are escaped; a # comment in a code block is not the title."""
    folder = tmp_path / EXPLAIN_DIR / "0001-pipes"
    folder.mkdir(parents=True)
    (folder / "README.md").write_text(
        "```bash\n# install first\n```\n\n# Input | output [v2]\n", encoding="utf-8"
    )

    text = index_markdown(read_entries(tmp_path / EXPLAIN_DIR))

    assert r"[Input \| output \[v2\]](0001-pipes/README.md)" in text
    assert "install first" not in text


def test_explainers_from_before_the_folders_are_listed(tmp_path: Path) -> None:
    """docs/explain/<slug>.md from the older layout still shows up in the index."""
    directory = tmp_path / EXPLAIN_DIR
    directory.mkdir(parents=True)
    (directory / "shop.md").write_text(EXPLAINER, encoding="utf-8")

    text = re.sub(r" +", " ", index_markdown(read_entries(directory)))

    assert "| | [Contact form](shop.md) | feature | 2026-09-26 |" in text


def test_a_hand_written_index_is_not_overwritten(tmp_path: Path) -> None:
    """A docs/explain/README.md that KingmaDoc did not write is kept, with a warning."""
    directory = tmp_path / EXPLAIN_DIR
    directory.mkdir(parents=True)
    (directory / "README.md").write_text("# My notes\n", encoding="utf-8")

    result = _new(tmp_path, "Checkout")

    assert result.exit_code == 0, result.output
    assert (directory / "README.md").read_text(encoding="utf-8") == "# My notes\n"
    assert "not written by KingmaDoc" in result.output


def test_an_explainer_with_windows_line_endings_gives_a_clean_index(tmp_path: Path) -> None:
    """CRLF files: the title and scope carry no carriage return into the index row."""
    folder = tmp_path / EXPLAIN_DIR / "0001-contact-form"
    folder.mkdir(parents=True)
    (folder / "README.md").write_bytes(EXPLAINER.replace("\n", "\r\n").encode("utf-8"))

    text = index_markdown(read_entries(tmp_path / EXPLAIN_DIR))

    assert "\r" not in text
    assert "[Contact form](0001-contact-form/README.md)" in text
