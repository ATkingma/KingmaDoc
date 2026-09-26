"""Checks for the Markdown-only agent skill in ``skill/SKILL.md``."""

import importlib.util
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.verify.stub import render_verify_stub

SKILL = Path(__file__).resolve().parents[1] / "skill" / "SKILL.md"


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
    """The fenced ``markdown`` block that follows the ``### <title>`` heading in SKILL.md."""
    after = _skill().split(f"### {title}", 1)[1]
    match = re.search(r"^(`{3,})markdown\n(.*?)\n\1$", after, re.S | re.M)
    assert match, f"no markdown block after {title!r}"
    return match.group(2)


def test_frontmatter() -> None:
    """Frontmatter follows the Agent Skills standard (A1) plus the requested fields."""
    meta = yaml.safe_load(_skill().split("---", 2)[1])

    assert meta["name"] == "kingmadoc"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
    assert meta["version"] == "1.0.0"
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
    assert len(text.splitlines()) < 400


def test_plan_format_matches_cli_template(tmp_path: Path) -> None:
    """The skill's plan format has exactly the headings the CLI renders."""
    result = CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )
    assert result.exit_code == 0, result.output

    assert _headings(_format_block("Plan doc")) == _headings(result.stdout)


def test_verify_format_matches_cli_stub() -> None:
    """The skill's verify format has exactly the headings of the CLI stub."""
    stub = render_verify_stub("add-login", "docs/features/add-login-plan.md",
                              now=datetime(2026, 1, 1, tzinfo=UTC))

    assert _headings(_format_block("Verify doc")) == _headings(stub)


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
        expected = build.build_variant(variant, _skill())

        assert path.read_text(encoding="utf-8") == expected, (
            f"{path.name} is stale: run python3 scripts/build_skill_variants.py"
        )


def test_agent_variants_follow_their_formats() -> None:
    """Cursor gets rule frontmatter; the always-loaded files get none; no Claude tool names."""
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
        assert _headings(text) == _headings(_skill()), name
