"""Checks for the `explaining-code` agent skill (roadmap WP12)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

SKILL = Path(__file__).resolve().parents[1] / "skill" / "explaining-code" / "SKILL.md"

EXPLAINER_HEADINGS = [
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


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _output_block() -> str:
    block = re.search(r"^(`{4,})markdown\n(.*?)\n\1$", _text(), re.S | re.M)
    assert block, "no ````markdown output format block"
    return block.group(2)


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
    meta = yaml.safe_load(_text().split("---", 2)[1])

    assert meta["name"] == SKILL.parent.name == "explaining-code"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
    assert 0 < len(meta["description"]) <= 1024
    assert "Use when" in meta["description"]
    for scope in ("feature", "branch", "project"):
        assert scope in meta["description"]


def test_workflow_sections_in_order_and_short() -> None:
    """The workflow is complete, in order, and the skill stays compact."""
    text = _text()
    sections = [
        "## When to use this skill",
        "## Step 1. Pin down the scope",
        "## Step 2. Read the code",
        "## Step 3. Draw it",
        "## Step 4. Write the explainer",
        "## Step 5. Render the pictures",
        "## Step 6. Hand it over",
        "## Output format",
    ]
    positions = [text.find(f"\n{s}\n") for s in sections]

    assert -1 not in positions, [s for s, p in zip(sections, positions, strict=True) if p == -1]
    assert positions == sorted(positions)
    assert len(text.splitlines()) < 350


def test_explainer_format_is_about_understanding_not_auditing() -> None:
    """Pictures and flows, no risk list, at most three questions."""
    block = re.sub(r"[ \t]+", " ", _output_block())  # the formatter pads table cells

    assert _headings(block) == EXPLAINER_HEADINGS
    assert "Risks" not in block and "Scope (in / out)" not in block
    assert block.count("```d2") >= 5  # context, containers, a component, a flow, data
    # Every figure is numbered and decoded by tables (lessons from design-doc reviews).
    assert "**Figure 1.**" in block and "**Figure 2.**" in block
    assert "| Part | Role | Technology |" in block
    assert "| From | To | What | How |" in block
    assert "| Chosen | Instead of | Why |" in block
    text = _text()
    assert "Do not change source code" in text
    assert "at most three" in text
    assert "kingmadoc render" in text


def _d2_examples() -> list[str]:
    return [m.group(1) for m in re.finditer(r"^```d2\n(.*?)\n```$", _text(), re.S | re.M)]


def test_skill_has_d2_examples() -> None:
    """The skill shows D2 for each kind of picture it asks for."""
    assert len(_d2_examples()) >= 4


D2 = os.environ.get("D2_BIN") or shutil.which("d2")


@pytest.mark.skipif(D2 is None, reason="d2 not available")
@pytest.mark.parametrize("index", range(12))
def test_d2_examples_compile(tmp_path: Path, index: int) -> None:
    """Agents copy these examples, so every one must compile with the real d2."""
    examples = _d2_examples()
    if index >= len(examples):
        pytest.skip("fewer examples")
    # Placeholders like <User> become plain text; arrows (->) must stay intact.
    source = re.sub(r"<([^<>\n]*)>", r"\1", examples[index])
    (tmp_path / "x.d2").write_text(source, encoding="utf-8")

    result = subprocess.run(
        [D2 or "d2", str(tmp_path / "x.d2"), str(tmp_path / "x.svg")],
        capture_output=True, text=True, timeout=60, check=False,
    )

    assert result.returncode == 0, f"example {index}:\n{examples[index]}\n{result.stderr}"
