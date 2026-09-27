"""Checks for the Markdown-only agent skill in ``skill/SKILL.md``."""

import importlib.util
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.verify.changes import Changes
from kingmadoc.verify.report import render_verify

SKILL = Path(__file__).resolve().parents[1] / "skill" / "SKILL.md"
REFERENCE = SKILL.parent / "reference"
FORMATS = REFERENCE / "formats.md"
DIAGRAM_RULES = REFERENCE / "diagram-rules.md"


def _skill() -> str:
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


def _format_block(title: str) -> str:
    """The fenced ``markdown`` block after the ``### <title>`` heading in reference/formats.md."""
    after = FORMATS.read_text(encoding="utf-8").split(f"### {title}", 1)[1]
    match = re.search(r"^(`{3,})markdown\n(.*?)\n\1$", after, re.S | re.M)
    assert match, f"no markdown block after {title!r}"
    return match.group(2)


def test_frontmatter() -> None:
    """Frontmatter follows the Agent Skills standard (A1) plus the requested fields."""
    meta = yaml.safe_load(_skill().split("---", 2)[1])

    assert meta["name"] == "kingmadoc"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
    assert meta["version"] == "1.1.0"
    assert meta["allowed-tools"] == ["Read", "Write", "Glob", "Grep", "Bash"]
    assert 0 < len(meta["description"]) <= 1024
    assert "Use when" in meta["description"]


def test_required_sections_and_length() -> None:
    """All requested sections exist, in order, and the file stays under 400 lines."""
    text = _skill()
    sections = [
        "## When to use this skill",
        "## Mode 1: plan",
        "## Mode 2: verify",
        "## Diagram rules",
        "## Output format",
    ]
    positions = [text.find(f"\n{s}\n") for s in sections]

    assert -1 not in positions
    assert positions == sorted(positions)
    assert len(text.splitlines()) < 250


def test_references_are_linked_and_short() -> None:
    """The formats and diagram rules live in reference/, one level deep, linked from SKILL.md."""
    text = _skill()
    for reference in (FORMATS, DIAGRAM_RULES):
        body = reference.read_text(encoding="utf-8")
        assert f"(reference/{reference.name})" in text, reference.name
        assert len(body.splitlines()) < 400, reference.name
    assert FORMATS.read_text(encoding="utf-8").startswith("## Output format\n")
    assert DIAGRAM_RULES.read_text(encoding="utf-8").startswith("## Diagram rules\n")


def test_links_into_the_references_resolve() -> None:
    """Every reference/<file>.md#anchor link in SKILL.md points at a heading of that file."""
    for file, anchor in re.findall(r"\]\(reference/([\w-]+\.md)#([\w-]+)\)", _skill()):
        text = re.sub(r"^(`{3,}).*?^\1$", "", (REFERENCE / file).read_text(encoding="utf-8"),
                      flags=re.S | re.M)
        headings = re.findall(r"^#{1,6} (.+)$", text, re.M)
        assert anchor in {_anchor(h) for h in headings}, f"{file}#{anchor}"


def _anchor(heading: str) -> str:
    """GitHub's anchor for a heading line."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def test_plan_format_matches_cli_template(tmp_path: Path) -> None:
    """The skill's plan format has exactly the headings the CLI renders."""
    result = CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )
    assert result.exit_code == 0, result.output

    assert _headings(_format_block("Plan doc")) == _headings(result.stdout)


def test_plan_format_has_the_cli_frontmatter(tmp_path: Path) -> None:
    """The skill writes the same frontmatter keys as the CLI, so `kingmadoc check` reads both."""
    result = CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )
    skill_block = _format_block("Plan doc")

    def keys(text: str) -> list[str]:
        return re.findall(r"^(\w+):", text.split("---\n", 2)[1], re.M)

    assert skill_block.startswith("---\n")
    assert keys(skill_block) == keys(result.stdout) == [
        "kingmadoc", "feature", "status", "requirements", "files_expected"
    ]
    assert "- **REQ-1**:" in skill_block


def test_verify_format_matches_cli_verify() -> None:
    """The skill's verify format has exactly the headings `kingmadoc verify` writes."""
    doc = render_verify(
        "add-login", "docs/features/add-login-plan.md", now=datetime(2026, 1, 1, tzinfo=UTC),
        status="Matches plan", changes=Changes("abc1234", (), "", None), deviations=(),
        commands=(), results=(),
    )

    assert _headings(_format_block("Verify doc")) == _headings(doc)


def test_technical_design_format_matches_template(tmp_path: Path) -> None:
    """The skill's technical design format has exactly the template's headings."""
    (tmp_path / ".featuredoc.yml").write_text(
        "extra_designs:\n  technical_design:\n    enabled: true\n", encoding="utf-8"
    )
    result = CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )
    assert result.exit_code == 0, result.output
    technical = result.stdout.split("\n---\n\n", 1)[1]

    assert _headings(_format_block("Technical design doc")) == _headings(technical)


def test_functional_design_format_matches_template(tmp_path: Path) -> None:
    """The skill's functional design format has exactly the template's headings."""
    (tmp_path / ".featuredoc.yml").write_text(
        "extra_designs:\n  functional_design:\n    enabled: true\n", encoding="utf-8"
    )
    result = CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )
    assert result.exit_code == 0, result.output
    functional = result.stdout.split("\n---\n\n", 1)[1]

    assert _headings(_format_block("Functional design doc")) == _headings(functional)


def _variants_module():
    """Import scripts/build_skill_variants.py (a repo script, not part of the package)."""
    path = SKILL.parents[1] / "scripts" / "build_skill_variants.py"
    spec = importlib.util.spec_from_file_location("build_skill_variants", path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses look their module up in sys.modules while the class is created.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_agent_variants_are_up_to_date() -> None:
    """skill/{cursor,codex,copilot}.md equal a fresh build from SKILL.md."""
    build = _variants_module()
    for variant in build.VARIANTS:
        path = SKILL.parent / variant.filename
        expected = build.build_variant(variant, _skill(), SKILL.parent)

        assert path.read_text(encoding="utf-8") == expected, (
            f"{path.name} is stale: run python3 scripts/build_skill_variants.py"
        )


def test_agent_variants_follow_their_formats() -> None:
    """Cursor gets rule frontmatter; the always-loaded files get none; no Claude tool names.

    The variants are single files, so the references are inlined in place of their stubs.
    """
    build = _variants_module()
    cursor = (SKILL.parent / "cursor.md").read_text(encoding="utf-8")
    meta = yaml.safe_load(cursor.split("---", 2)[1])
    assert meta == {
        "description": yaml.safe_load(_skill().split("---", 2)[1])["description"],
        "globs": None,
        "alwaysApply": False,
    }
    for name in ("codex.md", "copilot.md"):
        text = (SKILL.parent / name).read_text(encoding="utf-8")
        assert not text.startswith("---")
        assert "loaded in every session" in text
    for name in ("cursor.md", "codex.md", "copilot.md"):
        text = (SKILL.parent / name).read_text(encoding="utf-8")
        assert not re.search(r"\b(Glob|Grep|allowed-tools)\b", text), name
        expanded = build.expand_references(_skill(), SKILL.parent)
        assert _headings(text) == _headings(expanded), name
