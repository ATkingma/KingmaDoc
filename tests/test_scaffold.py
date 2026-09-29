"""``kingmadoc explain scaffold``: empty explainers built from the skill's own formats."""

import re
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.config import EXPLAIN_MODELS
from kingmadoc.exceptions import ExplainError
from kingmadoc.scaffold import (
    REFERENCE_FILES,
    KeyFacts,
    drop_sections,
    number_figures,
    output_block,
    scaffold,
)

REFERENCE = Path(__file__).resolve().parents[1] / "skill" / "explaining-code" / "reference"
REFERENCES = {name: (REFERENCE / name).read_text(encoding="utf-8") for name in REFERENCE_FILES}
FACTS = KeyFacts("Shop", "branch `feature/x` vs `main`", "Django, Python", "`manage.py`",
                 "abc1234", "2026-09-28", "9.9.9")


def _headings(markdown: str) -> list[str]:
    headings, fence = [], False
    for line in markdown.splitlines():
        if line.startswith("```"):
            fence = not fence
        elif not fence and line.startswith("#"):
            headings.append(line)
    return headings


def _figures(markdown: str) -> list[int]:
    return [int(n) for n in re.findall(r"\*\*Figure (\d+)\.\*\*", markdown)]


def _build(fmt="arc42", documents="single", models=EXPLAIN_MODELS, branch=False) -> dict:
    return scaffold(REFERENCES, FACTS, fmt, documents, models, branch)


def test_single_arc42_has_every_section_and_filled_key_facts() -> None:
    doc = _build()["README.md"]

    assert doc.startswith("# Shop: architecture explained\n")
    assert "| **Stack** | Django, Python |" in doc
    based_on = "abc1234 · 2026-09-28 · KingmaDoc skill explaining-code 9.9.9 (arc42)"
    assert f"| **Based on** | {based_on} |" in doc
    for number in range(1, 14):
        assert re.search(rf"^## {number}\. ", doc, re.M), number
    assert "## 2. Starting situation" in doc and "## 3. Architecture constraints" in doc
    assert doc.index("## Document control") < doc.index("## 1. Introduction and goals")
    assert "## What changed" not in doc  # no branch
    # The functional part sits in section 3's Business context, the threat model in 8.
    business = doc.split("### Business context")[1].split("### Technical context")[0]
    assert "#### User stories" in business and "##### Evil user stories" in business
    assert "### Business rules" in doc and "#### Interaction:" in doc
    assert _figures(doc) == list(range(1, len(_figures(doc)) + 1))  # no gaps
    assert "<with user_stories" not in doc and "\n\n\n" not in doc


def test_split_writes_cover_fo_and_to() -> None:
    files = _build(documents="split", branch=True)

    assert list(files) == ["README.md", "functional.md", "technical.md"]
    cover, functional, technical = files.values()
    assert "(split) |" in cover and "[Technical design](technical.md)" in cover
    assert functional.startswith("# Shop: functional design\n")
    assert [h for h in _headings(functional) if h.startswith("## ")][:3] == [
        "## 1. Goal and users", "## 2. Context", "## 3. Domain model"]
    assert technical.startswith("# Shop: technical design\n\nFunctional side:")
    assert "| **Stack**" not in technical  # the key facts are on the cover
    assert "### Business context" not in technical and "### Technical context" in technical
    assert "(C4 level 2)" in technical and "(C4 level 3)" in technical
    assert "### Level 3: code of <component> (C4 level 4)" in technical  # required in a TO
    assert "## What changed" in technical and "**Figure 0.**" in technical
    for heading in ("### Business rules", "### Permissions", "### Edge cases",
                    "### Threat model"):
        assert heading in technical, heading
    assert "See [functional.md](functional.md)." in technical


@pytest.mark.parametrize(("documents", "names"), [
    ("functional", ["README.md", "functional.md"]),
    ("technical", ["README.md", "technical.md"]),
])
def test_only_an_fo_or_only_a_to(documents: str, names: list[str]) -> None:
    files = _build(documents=documents)

    assert list(files) == names
    other = "technical.md" if documents == "functional" else "functional.md"
    assert f"({other})" not in files["README.md"]
    assert "functional.md" not in files.get("technical.md", "")


def test_c4_format() -> None:
    doc = _build(fmt="c4")["README.md"]
    technical = _build(fmt="c4", documents="technical")["technical.md"]

    assert "## How it works" in doc and "### User stories" in doc
    assert "## In short" not in technical and "## Threat model" in technical
    assert "### Business rules" in technical


def test_switched_off_models_leave_no_sections() -> None:
    models = [m for m in EXPLAIN_MODELS
              if m not in ("screens", "evil_user_stories", "threat_model", "user_stories")]
    doc = _build(models=models)["README.md"]
    functional = _build(documents="functional", models=models)["functional.md"]

    for gone in ("Screen", "Evil user stories", "Threat model", "User stories", "US-1"):
        assert not any(gone in h for h in _headings(doc + functional)), gone
    assert _figures(doc) == list(range(1, len(_figures(doc)) + 1))


def test_helpers() -> None:
    text = "# T\n## A\nkeep\n```\n## not a heading\n```\n## B\n### B1\ngone\n## C\n"
    assert drop_sections(text, lambda bare: bare != "B") == \
        "# T\n## A\nkeep\n```\n## not a heading\n```\n## C\n"
    assert number_figures("**Figure 0.** **Figure 7.** **Figure 7.**") == \
        "**Figure 0.** **Figure 1.** **Figure 2.**"
    with pytest.raises(ExplainError):
        output_block("# nothing here")
    with pytest.raises(ExplainError):
        output_block("## Output format\n\nno block")
    with pytest.raises(ExplainError):
        scaffold({}, FACTS, "arc42", "single", EXPLAIN_MODELS, False)


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "manage.py").write_text("import django\n", encoding="utf-8")
    for args in (["init", "-q", "-b", "main"], ["add", "."],
                 ["-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "x"],
                 ["checkout", "-qb", "feature/x"]):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607
    return tmp_path


def test_cli_writes_the_folder_and_keeps_existing_documents(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    args = ["explain", "scaffold", "branch feature/x", "--root", str(root),
            "--documents", "split", "--base", "main"]

    result = CliRunner().invoke(cli, args)

    assert result.exit_code == 0, result.output
    folder = root / "docs" / "explain" / "0001-branch-feature-x"
    assert result.output.splitlines() == [str(folder / n) for n in
                                          ("README.md", "functional.md", "technical.md")]
    cover = (folder / "README.md").read_text(encoding="utf-8")
    assert "| **Scope** | branch `feature/x` vs `main` |" in cover
    assert "0001" in (root / "docs" / "explain" / "README.md").read_text(encoding="utf-8")
    again = CliRunner().invoke(cli, args)
    assert again.exit_code == 1 and "--force" in again.output
    assert CliRunner().invoke(cli, [*args, "--force"]).exit_code == 0
    bad = CliRunner().invoke(cli, [*args, "--force", "--models", "screenz"])
    assert bad.exit_code == 2 and "screenz" in bad.output


def test_lower_c4_blocks_start_from_the_contexts_actors() -> None:
    doc = _build()["README.md"]
    line = "<copy the context figure's people and external systems"
    assert doc.count(line) == 3  # containers, components, deployment
