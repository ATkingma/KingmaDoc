#!/usr/bin/env python3
"""Generate the Cursor, Codex and Copilot variants of ``skill/SKILL.md``.

``skill/SKILL.md`` is the single source. Each variant gets the agent's own header
(Cursor rule frontmatter, or none for AGENTS.md / copilot-instructions.md) and
agent-neutral wording for Claude Code tool names. Never edit the variants by hand.

Usage:
    python3 scripts/build_skill_variants.py          # write skill/{cursor,codex,copilot}.md
    python3 scripts/build_skill_variants.py --check  # exit 1 if any variant is out of date
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "SKILL.md"

# Claude Code tool names -> wording every agent understands. Each phrase must occur
# in SKILL.md, so a rewording there fails the build instead of leaking tool names.
NEUTRAL_TOOLS: tuple[tuple[str, str], ...] = (
    ("Otherwise use Glob/Grep (never read the whole codebase):",
     "Otherwise use file search and text search (never read the whole codebase):"),
    ("**Files.** Glob `**/*`,", "**Files.** List files matching `**/*`,"),
    ("frameworks with Grep on imports", "frameworks with a text search on imports"),
    ("If no slug was given, Glob `<output_dir>/*-plan.md`.",
     "If no slug was given, list `<output_dir>/*-plan.md`."),
)

ALWAYS_LOADED_NOTE = (
    "> These instructions are loaded in every session. Follow them only when the user\n"
    "> asks to plan, design or scope a feature, or to verify what was built against its\n"
    "> plan (see [When to use this skill](#when-to-use-this-skill)); otherwise ignore them.\n"
)


@dataclass(frozen=True)
class Variant:
    """One agent-specific copy of the skill.

    Attributes:
        filename: File in ``skill/``.
        agent: Agent name, for the generated-file comment.
        install_path: Where users put the file in their project.
        cursor_rule: Emit Cursor rule frontmatter (``.mdc``) instead of no frontmatter.
    """

    filename: str
    agent: str
    install_path: str
    cursor_rule: bool = False


VARIANTS: tuple[Variant, ...] = (
    Variant("cursor.md", "Cursor", ".cursor/rules/kingmadoc.mdc", cursor_rule=True),
    Variant("codex.md", "Codex", "AGENTS.md (repository root)"),
    Variant("copilot.md", "GitHub Copilot", ".github/copilot-instructions.md"),
)


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a ``---`` YAML frontmatter block from the Markdown body.

    Args:
        text: File content starting with ``---``.

    Returns:
        ``(metadata, body)``.

    Raises:
        ValueError: If there is no frontmatter.
    """
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    _, meta, body = text.split("---\n", 2)
    return yaml.safe_load(meta), body.lstrip("\n")


def build_variant(variant: Variant, skill_text: str) -> str:
    """Render one variant from the SKILL.md text.

    Args:
        variant: Which agent to build for.
        skill_text: Content of ``skill/SKILL.md``.

    Returns:
        The variant's full file content.

    Raises:
        ValueError: If a phrase in :data:`NEUTRAL_TOOLS` is missing from SKILL.md.
    """
    meta, body = split_frontmatter(skill_text)
    for old, new in NEUTRAL_TOOLS:
        if old not in body:
            raise ValueError(f"SKILL.md no longer contains {old!r}; update NEUTRAL_TOOLS")
        body = body.replace(old, new)

    comment = (
        f"<!-- KingmaDoc {meta['version']} for {variant.agent}. Generated from "
        f"skill/SKILL.md by scripts/build_skill_variants.py; do not edit by hand.\n"
        f"     Install as: {variant.install_path} -->\n"
    )
    if variant.cursor_rule:
        # Agent-requested rule: Cursor loads it when the description matches the request.
        header = (
            "---\n"
            f"description: {json.dumps(meta['description'])}\n"
            "globs:\n"
            "alwaysApply: false\n"
            "---\n"
        )
        return header + comment + "\n" + body
    title, _, rest = body.partition("\n")
    return comment + "\n" + title + "\n\n" + ALWAYS_LOADED_NOTE + rest


def main(argv: list[str]) -> int:
    """Write (or with ``--check``, verify) all variants.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        Process exit code.
    """
    check = "--check" in argv
    skill_text = SKILL.read_text(encoding="utf-8")
    stale = []
    for variant in VARIANTS:
        path = SKILL.parent / variant.filename
        content = build_variant(variant, skill_text)
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(path.name)
        else:
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print(f"Out of date: {', '.join(stale)}; run scripts/build_skill_variants.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
