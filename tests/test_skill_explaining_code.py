"""Checks for the `explaining-code` agent skill (roadmap WP12)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

FOLDER = Path(__file__).resolve().parents[1] / "skill" / "explaining-code"
SKILL = FOLDER / "SKILL.md"
ARC42 = FOLDER / "reference" / "arc42.md"
C4 = FOLDER / "reference" / "c4.md"
REFERENCES = sorted((FOLDER / "reference").glob("*.md"))

ARC42_HEADINGS = [
    "#",
    "## What changed",
    "## 1. Introduction and goals",
    "## 2. Constraints",
    "## 3. Context and scope",
    "## 4. Solution strategy",
    "## 5. Building block view",
    "### Level 1: containers",
    "### Level 2: components of",
    "### Level 3: code of",
    "## 6. Runtime view",
    "###",
    "## 7. Deployment view",
    "## 8. Cross-cutting concepts",
    "## 9. Architecture decisions",
    "## 10. Quality requirements",
    "## 11. Risks and technical debt",
    "## 12. Glossary",
    "## Appendix: where to find what",
    "## Couldn't work out",
]

C4_HEADINGS = [
    "#",
    "## In short",
    "## Terms",
    "## Context",
    "## Containers",
    "## Components",
    "###",
    "## How it works",
    "###",
    "## Routes and permissions",
    "## Data",
    "## Configuration",
    "## What changed",
    "## Design choices",
    "## Where to find what",
    "## Couldn't work out",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _output_block(path: Path) -> str:
    block = re.search(r"^(`{4,})markdown\n(.*?)\n\1$", _read(path), re.S | re.M)
    assert block, f"no ````markdown output format block in {path.name}"
    return re.sub(r"[ \t]+", " ", block.group(2))  # the formatter pads table cells


def _headings(markdown: str) -> list[str]:
    """Headings outside ``` blocks, reduced to their fixed part (placeholders removed)."""
    headings, in_code = [], False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and line.startswith("#"):
            headings.append(re.sub(r"<[^>]*>.*$|\s+\(.*$", "", line).strip())
    return headings


def test_frontmatter_follows_the_agent_skills_standard() -> None:
    """Name matches the folder (required by Cursor); description says when to use it."""
    meta = yaml.safe_load(_read(SKILL).split("---", 2)[1])

    assert meta["name"] == FOLDER.name == "explaining-code"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
    assert 0 < len(meta["description"]) <= 1024
    assert "Use when" in meta["description"]
    for word in ("feature", "branch", "project", "arc42"):
        assert word in meta["description"]


def test_description_triggers_on_the_ways_people_ask() -> None:
    """Agents pick a skill by its description (the model matches meaning, in any language)."""
    description = yaml.safe_load(_read(SKILL).split("---", 2)[1])["description"]

    for trigger in (
        "explain", "document", "diagram", "overview", "how something works", "what it does",
        "PR", "onboarding", "walkthrough", "C4", "UML", "any language",
        "Not for features that are not built yet",
    ):
        assert trigger in description, trigger


def test_workflow_sections_in_order_and_short() -> None:
    """The workflow is complete, in order; details live in reference files (one level)."""
    text = _read(SKILL)
    sections = [
        "## When to use this skill",
        "## Step 1. Pin down the scope, the format and the documents",
        "## Step 2. Read the code",
        "## Step 3. Choose the models and draw them",
        "## Step 4. Write the explainer",
        "## Step 5. Render the pictures",
        "## Step 6. Check and hand it over",
    ]
    positions = [text.find(f"\n{s}\n") for s in sections]

    assert -1 not in positions, [s for s, p in zip(sections, positions, strict=True) if p == -1]
    assert positions == sorted(positions)
    for reference in REFERENCES:  # every reference file is linked from SKILL.md
        assert f"reference/{reference.name}" in text, reference.name
        assert len(_read(reference).splitlines()) < 400, reference.name
    assert len(text.splitlines()) < 300


def test_skill_rules() -> None:
    """Explain, don't audit; pictures; at most three questions."""
    text = _read(SKILL)

    assert "Do not change source code" in text
    assert "at most three" in text
    assert "kingmadoc render" in text
    assert "explain.format" in text
    assert "explain.documents" in text


def test_each_subject_gets_its_own_folder() -> None:
    """Output goes to docs/explain/<NNNN>-<slug>/README.md, picked by `kingmadoc explain new`."""
    text = _read(SKILL)
    version = yaml.safe_load(text.split("---", 2)[1])["version"]

    assert "kingmadoc explain new" in text
    assert "docs/explain/<NNNN>-<slug>/README.md" in text
    assert "docs/explain/<slug>.md" not in text
    for reference in (ARC42, C4):  # the "Based on" row names the current skill version
        assert f"explaining-code {version}" in _read(reference), reference.name


def test_skill_never_sends_the_user_to_install_d2() -> None:
    """render downloads D2 itself; updating uses `pipx upgrade` (a git install: `pipx reinstall`; --force can fail)."""
    text = _read(SKILL)

    assert "Never ask the user to install D2" in text
    assert "pipx upgrade kingmadoc" in text and "pipx reinstall kingmadoc" in text
    assert "install --force" not in text


def test_arc42_format() -> None:
    """The default format has the 12 arc42 sections, in order, with numbered figures."""
    block = _output_block(ARC42)

    assert _headings(block) == ARC42_HEADINGS
    assert block.count("```d2") >= 6  # context, containers, components, code, flow, deployment
    assert "**Figure 1.**" in block and "**Figure 2.**" in block
    assert "| Part | Role | Technology |" in block
    assert "| From | To | What | How |" in block
    # arc42 sections 10 and 11 only report what is documented: no risk hunting.
    assert "only what is documented" in _read(ARC42)
    assert "C4 level 4" in _read(ARC42)


def test_c4_format() -> None:
    """The compact format zooms in and decodes every figure with tables."""
    block = _output_block(C4)

    assert _headings(block) == C4_HEADINGS
    assert "Risks" not in block and "Scope (in / out)" not in block
    assert block.count("```d2") >= 5
    assert "**Figure 1.**" in block and "**Figure 2.**" in block
    assert "| Part | Role | Technology |" in block
    assert "| From | To | What | How |" in block
    assert "| Chosen | Instead of | Why |" in block


def _d2_examples() -> list[str]:
    return [
        m.group(1)
        for path in (SKILL, *REFERENCES)
        for m in re.finditer(r"^```d2\n(.*?)\n```$", _read(path), re.S | re.M)
    ]


def test_skill_has_d2_examples() -> None:
    """The skill shows D2 for each kind of picture it asks for."""
    assert len(_d2_examples()) >= 8


D2 = os.environ.get("D2_BIN") or shutil.which("d2")


@pytest.mark.skipif(D2 is None, reason="d2 not available")
@pytest.mark.parametrize("index", range(60))
def test_d2_examples_compile(tmp_path: Path, index: int) -> None:
    """Agents copy these examples, so every one must compile with the real d2."""
    examples = _d2_examples()
    if index >= len(examples):
        pytest.skip("fewer examples")
    # Placeholders like <User> become plain text; arrows (->, <->) must stay intact.
    source = re.sub(r"<([A-Za-z][^<>\n]*)>", r"\1", examples[index])
    (tmp_path / "x.d2").write_text(source, encoding="utf-8")

    result = subprocess.run(
        [D2 or "d2", str(tmp_path / "x.d2"), str(tmp_path / "x.svg")],
        capture_output=True, text=True, timeout=60, check=False,
    )

    assert result.returncode == 0, f"example {index}:\n{examples[index]}\n{result.stderr}"


def test_explaining_again_starts_from_explain_status() -> None:
    """Re-explaining checks what changed since the Based on commit, which needs the commit."""
    text = re.sub(r"\s+", " ", _read(SKILL))

    assert "kingmadoc explain status" in text
    assert "code spans" in text
    for reference in (ARC42, C4):
        assert "| **Based on** | <commit hash" in re.sub(r"[ \t]+", " ", _read(reference))


def test_reading_the_code_starts_from_the_facts() -> None:
    """Step 2 runs `kingmadoc explain facts` (with --base for a branch) before reading."""
    step = _read(SKILL).split("## Step 2.", 1)[1].split("## Step 3.", 1)[0]

    assert "kingmadoc explain facts" in step
    assert "--base" in step
    assert "never contradict" in step
