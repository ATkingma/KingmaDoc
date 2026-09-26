"""Checks for the `documenting-existing-features` agent skill (roadmap WP12)."""

import re
from pathlib import Path

import yaml
from click.testing import CliRunner

from kingmadoc.cli import cli

SKILL = (
    Path(__file__).resolve().parents[1] / "skill" / "documenting-existing-features" / "SKILL.md"
)


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _headings(markdown: str) -> list[str]:
    """Markdown headings outside ``` code blocks, with ``<placeholders>`` removed."""
    headings, in_code = [], False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and line.startswith("#"):
            headings.append(re.sub(r"<[^>]*>|:\s.*$", "", line).strip())
    return headings


def test_frontmatter_follows_the_agent_skills_standard() -> None:
    """Name matches the folder (required by Cursor), description says when to use it."""
    meta = yaml.safe_load(_text().split("---", 2)[1])

    assert meta["name"] == SKILL.parent.name == "documenting-existing-features"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
    assert 0 < len(meta["description"]) <= 1024
    assert "Use when" in meta["description"]
    assert meta["allowed-tools"] == ["Read", "Write", "Glob", "Grep", "Bash"]


def test_required_sections_and_length() -> None:
    """The workflow sections exist in order, and the skill stays well under 500 lines."""
    text = _text()
    sections = [
        "## When to use this skill",
        "## Step 1. Pin down the feature",
        "## Step 2. Find the code",
        "## Step 3. Understand what it does",
        "## Step 4. Write the as-built document",
        "## Step 5. Check with the user",
        "## Output format",
    ]
    positions = [text.find(f"\n{s}\n") for s in sections]

    assert -1 not in positions, [s for s, p in zip(sections, positions, strict=True) if p == -1]
    assert positions == sorted(positions)
    assert len(text.splitlines()) < 400


def test_output_format_is_the_plan_format_plus_implementation_map(tmp_path: Path) -> None:
    """As-built docs use the plan's headings, so verify and the design models work on them."""
    block = re.search(r"^(`{3,})markdown\n(.*?)\n\1$", _text(), re.S | re.M)
    assert block, "no markdown output block"
    result = CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )
    assert result.exit_code == 0, result.output

    expected = [*_headings(result.stdout), "## Appendix"]  # + implementation map appendix
    assert _headings(block.group(2)) == expected


def test_it_never_changes_source_code() -> None:
    """The skill states that it only writes documentation."""
    assert "Do not change source code" in _text()
