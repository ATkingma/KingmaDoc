"""Empty explainer documents for the explaining-code skill (``kingmadoc explain scaffold``).

The skill's reference files are the one source of every output format (agents without
the CLI read them directly). This module cuts those ``markdown`` blocks out, puts them
together for the chosen format, documents and models, fills in what is known without
reading code (stack, entry points, commit, date, versions), numbers the figures and
returns the files. The agent then only fills in the ``<placeholders>``; it no longer
needs to read the output formats itself.

Pure: the caller reads the reference files and writes the result.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from kingmadoc.exceptions import ExplainError

# The reference files the formats are read from (keys of ``references``).
REFERENCE_FILES: tuple[str, ...] = ("arc42.md", "c4.md", "split.md", "threat-model.md")

_BLOCK = re.compile(r"^(`{3,})markdown\n(.*?)\n\1$", re.S | re.M)
_HEADING = re.compile(r"^(#{1,6}) (.+)$")
_FENCE = re.compile(r"^(`{3,}|~{3,})")
_FIGURE = re.compile(r"\*\*Figure (\d+)\.\*\*")
_NUMBER = re.compile(r"^\d+\.\s+")

# Model (``explain.models``) -> headings of the parts that only exist for it.
MODEL_SECTIONS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "user_stories": ("User stories", "Per user story", "US-1"),
    "screens": ("Screen",),
    "evil_user_stories": ("Evil user stories",),
    "activity": ("Activity",),
    "domain_model": ("Domain model",),
    "state_machine": ("Lifecycle of",),
    "threat_model": ("Threat model",),
    "c4_code": ("Level 3: code of",),
    "c4_component": ("Components", "Level 2: components of"),
    "c4_deployment": ("Deployment",),
    "use_case": ("What users can do",),
})


@dataclass(frozen=True)
class KeyFacts:
    """What the key facts table says, known without reading the code.

    Attributes:
        name: Subject name, the document title.
        scope: E.g. "project", "feature", "branch `feature/x` vs `main`".
        stack: Languages, frameworks and data stores, comma-separated.
        entry_points: Code spans, e.g. "`manage.py`, `shop/urls.py`".
        commit: Short hash of the commit it is based on (may be empty).
        date: ISO date.
        version: The explaining-code skill's version.
    """

    name: str
    scope: str
    stack: str
    entry_points: str
    commit: str
    date: str
    version: str


def output_block(reference: str, title: str = "Output format") -> str:
    """The ``markdown`` block after the ``## <title>`` heading of a reference file.

    Raises:
        ExplainError: If the heading or its block is missing.
    """
    head = f"## {title}\n"
    if head not in reference:
        raise ExplainError(f"No '## {title}' section in the skill's reference files")
    match = _BLOCK.search(reference.split(head, 1)[1])
    if not match:
        raise ExplainError(f"No markdown block under '## {title}'")
    return match.group(2)


def _heading_text(line: str) -> tuple[int, str] | None:
    match = _HEADING.match(line)
    if not match:
        return None
    return len(match.group(1)), match.group(2)


def _bare(text: str) -> str:
    """Heading text without numbering, placeholders and "(optional)"-style notes."""
    text = _NUMBER.sub("", text)
    text = re.sub(r"\s*\((?:optional|branch only)[^)]*\)", "", text)
    return text.strip()


def _lines_outside_code(markdown: str) -> list[tuple[str, bool]]:
    """Every line with whether it belongs to a fenced code block (fences included)."""
    result, fence = [], ""
    for line in markdown.split("\n"):
        match = _FENCE.match(line)
        if fence:
            result.append((line, True))
            if match and line.strip() == match.group(1) and match.group(1)[0] == fence[0] \
                    and len(match.group(1)) >= len(fence):
                fence = ""
            continue
        if match:
            fence = match.group(1)
        result.append((line, bool(match)))
    return result


def drop_sections(markdown: str, wanted: Callable[[str], bool]) -> str:
    """Remove every section whose bare heading text makes ``wanted`` return False.

    A section runs from its heading to the next heading of the same or a higher level.
    """
    out: list[str] = []
    skip_level = 0
    for line, in_code in _lines_outside_code(markdown):
        heading = None if in_code else _heading_text(line)
        if heading:
            level, text = heading
            if skip_level and level <= skip_level:
                skip_level = 0
            if not skip_level and not wanted(_bare(text)):
                skip_level = level
                continue
        if not skip_level:
            out.append(line)
    return "\n".join(out)


def shift_headings(markdown: str, by: int) -> str:
    """Move every heading (outside code) ``by`` levels deeper (or up when negative)."""
    out = []
    for line, in_code in _lines_outside_code(markdown):
        heading = None if in_code else _heading_text(line)
        if heading:
            level = min(6, max(1, heading[0] + by))
            line = "#" * level + " " + heading[1]
        out.append(line)
    return "\n".join(out)


def section(markdown: str, bare_title: str, with_heading: bool = False) -> str:
    """The body of the first section whose bare heading is ``bare_title`` (or empty)."""
    lines = _lines_outside_code(markdown)
    for index, (line, in_code) in enumerate(lines):
        heading = None if in_code else _heading_text(line)
        if heading and _bare(heading[1]) == bare_title:
            body = []
            for other, other_in_code in lines[index + 1:]:
                other_heading = None if other_in_code else _heading_text(other)
                if other_heading and other_heading[0] <= heading[0]:
                    break
                body.append(other)
            text = "\n".join(body).strip("\n")
            return f"{line}\n\n{text}" if with_heading else text
    return ""


def replace_section_body(markdown: str, bare_title: str, body: str) -> str:
    """Replace the body of a section (its heading stays) with ``body``."""
    lines = _lines_outside_code(markdown)
    for index, (line, in_code) in enumerate(lines):
        heading = None if in_code else _heading_text(line)
        if heading and _bare(heading[1]) == bare_title:
            end = len(lines)
            for offset, (other, other_in_code) in enumerate(lines[index + 1:], index + 1):
                other_heading = None if other_in_code else _heading_text(other)
                if other_heading and other_heading[0] <= heading[0]:
                    end = offset
                    break
            before = [text for text, _ in lines[: index + 1]]
            after = [text for text, _ in lines[end:]]
            return "\n".join([*before, "", body.strip("\n"), "", *after])
    return markdown


def number_figures(markdown: str) -> str:
    """Number the figure captions 1, 2, 3 … in document order (Figure 0 stays 0)."""
    counter = 0

    def renumber(match: re.Match[str]) -> str:
        nonlocal counter
        if match.group(1) == "0":
            return match.group(0)
        counter += 1
        return f"**Figure {counter}.**"

    return _FIGURE.sub(renumber, markdown)


def _fill_key_facts(markdown: str, facts: KeyFacts, variant: str) -> str:
    based_on = " · ".join(p for p in (facts.commit, facts.date) if p)
    rows = {
        "Scope": facts.scope,
        "Stack": facts.stack or "<languages, frameworks, data stores>",
        "Entry points": facts.entry_points or "<`path`, …>",
        "Based on": f"{based_on} · KingmaDoc skill explaining-code {facts.version}"
        + (f" ({variant})" if variant else ""),
    }
    for label, value in rows.items():
        row = f"| **{label}** | {value} |".replace("\\", "\\\\")
        markdown = re.sub(
            rf"^\|[ \t]*\*\*{re.escape(label)}\*\*[ \t]*\|.*\|[ \t]*$",
            row, markdown, count=1, flags=re.M,
        )
    markdown = re.sub(r"^\|\s+\|\s+\|\n\|\s*-+\s*\|\s*-+\s*\|", "| | |\n|---|---|", markdown,
                      count=1, flags=re.M)
    return markdown.replace("<Name>", facts.name)


def _keep(models: Sequence[str], branch: bool) -> Callable[[str], bool]:
    """Section filter: drop parts of switched-off models, and branch-only parts."""
    off = [heading for model, headings in MODEL_SECTIONS.items() if model not in models
           for heading in headings]

    def wanted(bare: str) -> bool:
        if bare == "What changed" and not branch:
            return False
        return not any(bare == h or bare.startswith(h + ":") or bare.startswith(h + " ")
                       for h in off)

    return wanted


def _clean(markdown: str, branch: bool) -> str:
    markdown = markdown.replace(" (branch only)", "") if branch else markdown
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip() + "\n"


def _stories(functional: str) -> str:
    """The FO's use case, user story and per-story parts, for inside another document."""
    parts = [
        section(functional, "What users can do"),
        re.sub(r"^(#+) \d+\. ", r"\1 ",
               shift_headings(section(functional, "User stories", with_heading=True), 2),
               flags=re.M),
        shift_headings(section(functional, "Per user story"), 1),
    ]
    return "\n\n".join(p for p in parts if p.strip())


def _technical(
    base: str, fmt: str, rules: str, threat_model: str, with_functional: bool
) -> str:
    """The chosen format turned into a technical design (TO), as split.md says."""
    title, _, rest = base.partition("\n")
    title = re.sub(r":.*$", ": technical design", title)
    rest = re.sub(r"^\|[^\n]*\|\n(?:\|[^\n]*\|\n)*", "", rest.lstrip("\n"), count=1)
    first = "Functional side: [functional.md](functional.md)." if with_functional else ""
    doc = f"{title}\n\n{first}\n\n{rest}"
    see_fo = ("What it does and for whom: [functional.md](functional.md)."
              if with_functional else "<one line: what it does and for whom>")
    if fmt == "arc42":
        doc = re.sub(r"(## 1\. Introduction and goals\n).*?(?=\n## )", rf"\1\n{see_fo}\n",
                     doc, count=1, flags=re.S)
        doc = drop_sections(doc, lambda bare: bare != "Business context")
        doc = replace_section_body(doc, "Threat model", threat_model)
        doc = doc.replace("### Threat model (optional)", "### Threat model")
        doc = doc.replace("(optional, C4 level 4)", "(C4 level 4)")
        doc = doc.replace("\n### Threat model\n", f"\n{rules}\n\n### Threat model\n", 1)
        if with_functional:
            doc = replace_section_body(doc, "Glossary",
                                       "See [functional.md](functional.md).")
    else:
        doc = drop_sections(doc, lambda bare: bare not in ("In short", "Terms"))
        doc = replace_section_body(
            doc, "Routes and permissions",
            section(doc, "Routes and permissions") + "\n\n" + shift_headings(rules, 0),
        )
        doc = doc.replace("## Routes and permissions (optional)", "## Routes and permissions")
        doc = replace_section_body(doc, "Threat model", shift_headings(threat_model, -1))
        doc = doc.replace("## Threat model (optional)", "## Threat model")
    return doc


def scaffold(
    references: Mapping[str, str],
    facts: KeyFacts,
    fmt: str,
    documents: str,
    models: Sequence[str],
    branch: bool,
) -> dict[str, str]:
    """The explainer's files, empty but for what is known, keyed by file name.

    Args:
        references: File name -> text of the skill's reference files
            (:data:`REFERENCE_FILES`).
        facts: The key facts table's content.
        fmt: ``arc42`` or ``c4``.
        documents: ``single``, ``split``, ``functional`` or ``technical``.
        models: The models that may be drawn (``explain.models``).
        branch: Whether the subject is a branch (keeps "What changed").

    Raises:
        ExplainError: If a reference or one of its output formats is missing.
    """
    missing = [name for name in REFERENCE_FILES if name not in references]
    if missing:
        raise ExplainError(f"Missing reference files: {', '.join(missing)}")
    split = references["split.md"]
    base = output_block(references[f"{fmt}.md"])
    functional = output_block(split, "Output format: functional.md")
    threat_model = output_block(references["threat-model.md"])
    if threat_model.startswith("### "):  # its heading comes from the document
        threat_model = threat_model.split("\n", 1)[1]
    rules = output_block(split, "Rules, permissions and edge cases")
    keep = _keep(models, branch)

    def finish(markdown: str, variant: str) -> str:
        markdown = drop_sections(markdown, keep)
        return _clean(number_figures(_fill_key_facts(markdown, facts, variant)), branch)

    if documents == "single":
        doc = base
        stories = _stories(functional) if "user_stories" in models else ""
        if fmt == "arc42":
            doc = re.sub(r"^<with user_stories:.*?>\n", (stories + "\n") if stories else "",
                         doc, count=1, flags=re.S | re.M)
            doc = replace_section_body(doc, "Threat model", threat_model)
            doc = doc.replace("\n### Threat model (optional)\n",
                              f"\n{rules}\n\n### Threat model (optional)\n", 1)
        elif stories:
            doc = doc.replace("## How it works\n",
                              f"## How it works\n\n{shift_headings(stories, -1)}\n", 1)
        return {"README.md": finish(doc, fmt)}

    cover = output_block(split, "Output format: README.md (cover)")
    files: dict[str, str] = {}
    if documents in ("split", "functional"):
        files["functional.md"] = functional
    if documents in ("split", "technical"):
        files["technical.md"] = _technical(base, fmt, rules, threat_model,
                                           with_functional=documents == "split")
    rows = (("functional.md", "Functional design"), ("technical.md", "Technical design"))
    for name, row in rows:
        if name not in files:
            cover = "\n".join(line for line in cover.split("\n") if f"[{row}]" not in line)
    if documents == "technical" and "technical.md" in files:
        files["technical.md"] = files["technical.md"].replace(
            "Functional side: [functional.md](functional.md).\n", "")
    result = {"README.md": finish(cover, documents)}
    for name, text in files.items():
        result[name] = finish(text, "")
    return result
