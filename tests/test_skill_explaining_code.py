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
    "## Document control",
    "## What changed",
    "## 1. Introduction and goals",
    "## 2. Starting situation",
    "## 3. Architecture constraints",
    "## 4. Context and scope",
    "### Business context",
    "### Technical context",
    "## 5. Solution strategy",
    "## 6. Building block view",
    "### Level 1: containers",
    "### Level 2: components of",
    "### Level 3: code of",
    "## 7. Runtime view",
    "###",
    "## 8. Deployment view",
    "## 9. Cross-cutting concepts",
    "### Conventions",
    "### Threat model",
    "## 10. Architecture decisions",
    "## 11. Quality requirements",
    "## 12. Risks and technical debt",
    "## 13. Glossary",
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
    "## Threat model",
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
        "Not for features that are not built yet", "only the classes or files the user names",
        "new pattern",
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
        assert len(_read(reference).splitlines()) < 450, reference.name
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
    """render downloads D2 itself; updating uses `pipx upgrade` (git: `pipx reinstall`)."""
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

    # The same options as `kingmadoc render`: the ELK layout and the dark theme.
    from kingmadoc.render import D2_DARK_THEME, _layout_args

    result = subprocess.run(
        [D2 or "d2", *_layout_args(source), "--dark-theme", str(D2_DARK_THEME),
         str(tmp_path / "x.d2"), str(tmp_path / "x.svg")],
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
    assert "dominator tree" in step


def test_the_skill_keeps_the_agents_context_small() -> None:
    """Quiet work, references on demand, a subagent for big codebases, a short hand-over."""
    text = re.sub(r"\s+", " ", _read(SKILL))
    efficient = text.split("## Working efficiently", 1)[1].split("## Step 1", 1)[0]
    hand_over = text.split("## Step 6.", 1)[1]

    assert "only to ask" in efficient and "hand over" in efficient
    assert "subagent" in efficient and "--only" in efficient
    assert "table of contents" in efficient
    assert "at most five lines" in hand_over
    assert "and the figures" not in hand_over


def test_long_references_start_with_their_contents() -> None:
    """A reference over 100 lines lists its sections first, so a partial read shows them."""
    for path in sorted((SKILL.parent / "reference").glob("*.md")):
        lines = _read(path).splitlines()
        if len(lines) <= 100:
            continue
        head = re.sub(r"\s+", " ", " ".join(lines[:12]))
        assert "Contents:" in head, path.name
        for section in re.findall(r"^## (.+)$", _read(path).split("````", 1)[0], re.M):
            assert section.split(".")[0] in head or section in head, f"{path.name}: {section}"


def test_arrows_stay_tidy() -> None:
    """One flow direction, one arrow per pair, at most 12 arrows, short labels."""
    step = re.sub(r"\s+", " ", _read(SKILL).split("## Step 3.", 1)[1].split("## Step 4.", 1)[0])

    assert "direction: down" in step and "one arrow per pair" in step
    assert "at most 12 arrows" in step and "four words" in step


def test_hand_over_offers_the_vs_code_preview() -> None:
    """The pictures only show in a preview: ask once, then set it up on yes."""
    hand_over = re.sub(r"\s+", " ", _read(SKILL).split("## Step 6.", 1)[1])

    assert "kingmadoc skills install --vscode" in hand_over
    assert "Ask" in hand_over and "on yes" in hand_over


SPLIT = FOLDER / "reference" / "split.md"


def _split_block(title: str) -> str:
    """The ````markdown block after ``## <title>`` in reference/split.md."""
    after = _read(SPLIT).split(f"## {title}\n", 1)[1]
    block = re.search(r"^(`{4,})markdown\n(.*?)\n\1$", after, re.S | re.M)
    assert block, title
    return block.group(2)


def test_fo_to_and_arc42_requests_pick_their_variant() -> None:
    """"Document an arc42" -> arc42; "document an FO/TO" -> functional + technical."""
    text = _read(SKILL)
    description = yaml.safe_load(text.split("---", 2)[1])["description"]
    step = re.sub(r"\s+", " ", text.split("## Step 1.", 1)[1].split("## Step 2.", 1)[0])

    assert "arc42" in description and "(FO, TO, or only one of them)" in description
    assert "otherwise **single** (one arc42 document)" in step
    assert "without asking back" in step
    for request, documents in {
        '"document it as arc42"': "single",
        '"as an FO/TO"': "split",
        '"describe this branch with an FO and a TO"': "split",
        '"only an FO"': "functional",
        '"only a TO"': "technical",
    }.items():
        row = re.search(re.escape(request) + r"[^|]*\| `(\w+)`", step)
        assert row and row.group(1) == documents, request
    for documents in ("`split` (FO/TO)", "`functional` (FO)", "`technical` (TO)"):
        assert documents in step, documents


def test_functional_design_follows_one_red_thread() -> None:
    """User stories, then per story a use case, a screen and evil user stories."""
    block = _split_block("Output format: functional.md")

    assert _headings(block) == [
        "#", "## 1. Goal and users", "## 2. Context", "## 3. Domain model",
        "### Lifecycle of", "## 4. What users can do", "## 5. User stories",
        "## 6. Per user story", "### US-1:", "#### Use case", "#### Screen",
        "#### Activity", "#### Evil user stories", "## 7. Glossary",
        "## Couldn't work out",
    ]
    for row in ("| US-1 |", "| UC-1 ", "**Main scenario**", "**Exceptions**", "| EUS-1.1 |",
                "img/screen-us-1.png", "wireframe"):
        assert row in block, row
    assert "SM-1" in block  # evil user stories point at the technical measures


def test_threat_model_is_in_the_technical_design() -> None:
    """Microsoft Threat Modeling Tool style: stencils, STRIDE per interaction, states."""
    technical = _read(SPLIT).split("## Output format: technical.md", 1)[1]
    threat_model = FOLDER / "reference" / "threat-model.md"
    rules = re.sub(r"\s+", " ", _read(threat_model))
    block = _output_block(threat_model)

    assert "The [threat model](threat-model.md) is always there" in technical
    assert "Microsoft Threat Modeling Tool" in rules
    assert "#### Interaction: <flow name>" in block
    assert "| # | Threat" in block and "| State" in block and "| Priority" in block
    states = "| Not Started | Not Applicable | Needs Investigation | Mitigation Implemented |"
    assert states in block
    threats = _read(FOLDER / "reference" / "threats.md")
    for category in ("Spoofing", "Tampering", "Repudiation", "Information Disclosure",
                     "Denial Of Service", "Elevation Of Privilege"):
        assert f"| {category} |" in threats, category
    for stencil in ("External Interactor", "Process", "Data Store", "Internet Boundary"):
        assert stencil in rules, stencil
    assert "kingmadoc threats img/threat-model.yml" in rules
    assert "never invent threats outside it" in rules
    assert "#### Security measures" in block and "| SM-1 |" in block
    assert "threat model" in _read(ARC42).lower() and "## Threat model" in _read(C4)


def test_screens_never_block_the_explainer() -> None:
    """Wireframes first; screenshots only when allowed, offered at hand-over; no early question."""
    stories = re.sub(r"\s+", " ", _read(FOLDER / "reference" / "stories.md"))

    assert "The explainer never waits for it" in stories
    assert "Never ask before the document exists" in stories
    assert "kingmadoc screenshots <url>" in stories
    assert "Never change code or configuration" in stories
    assert '"[Screen]' in stories

def test_fo_is_for_stakeholders_and_to_for_developers() -> None:
    """Business rules, permissions and edge cases are technical: they live in the TO."""
    functional = _split_block("Output format: functional.md")
    rules = _split_block("Rules, permissions and edge cases")

    for technical in ("BR-1", "| May ", "Not allowed", "Edge cases", "`<path>`"):
        assert technical not in functional, technical
    for heading in ("### Business rules", "### Permissions", "### Edge cases"):
        assert heading in rules, heading
    assert "developers only" in _read(SPLIT) and "stakeholders" in _read(SPLIT)
    assert "rules-permissions-and-edge-cases" in _read(ARC42)


def test_arc42_follows_a_software_architecture_document() -> None:
    """Business vs technical context, stakeholders, conventions, tested quality scenarios."""
    guide = re.sub(r"\s+", " ", _read(ARC42))
    block = _output_block(ARC42)

    assert "**Business context** (for stakeholders" in guide
    assert "**Technical context** (for developers" in guide
    assert "| Stakeholder (optional) |" in block
    assert "| Scenario | Context | Quality goal | How it is tested |" in block
    assert "**conventions**: code, branches, commits" in guide
    assert "Tests are facts; do not grade them." in guide
    # Like a classic SAD: document control first, then where it all started.
    assert "| Version | Date | Author | Change |" in block
    assert "| Source | Used for |" in block
    assert "| Constraint | Background |" in block
    assert "by **general pattern**, never by class or part" in guide
    assert "passes / fails / doubt / out of scope" in guide
    assert "section 4 keeps only its Technical context" in re.sub(r"\s+", " ", _read(SPLIT))


def test_fo_starts_with_the_domain_model_and_to_has_all_c4_levels() -> None:
    """The domain model is the FO's overview; the TO zooms through C4 levels 2 to 4."""
    headings = _headings(_split_block("Output format: functional.md"))
    technical = re.sub(r"\s+", " ", _read(SPLIT).split("## Output format: technical.md")[1])

    assert headings.index("## 3. Domain model") < headings.index("## 4. What users can do")
    for level in ("C4 level 2 (containers)", "C4 level 3 (a component diagram",
                  "C4 level 4 (a class or ER diagram"):
        assert level in technical, level


def test_the_skill_always_delivers_rendered_pictures() -> None:
    """Never stop before the explainer is written and rendered; `explain check` is the gate."""
    text = re.sub(r"\s+", " ", _read(SKILL))
    rules = text.split("Rules:", 1)[1].split("## Working efficiently", 1)[0]
    step6 = text.split("## Step 6.", 1)[1]

    assert "**Always deliver the pictures.**" in rules
    assert "Never ask first and stop" in rules
    assert "kingmadoc explain check" in step6 and "repeat until it passes" in step6
    step1 = text.split("## Step 1.", 1)[1].split("## Step 2.", 1)[0]
    assert "ask one question" not in step1


def test_the_scaffold_is_filled_in_one_pass() -> None:
    """One write per document: filling placeholder by placeholder doubled the turns."""
    step = re.sub(r"\s+", " ", _read(SKILL).split("## Step 4.", 1)[1].split("## Step 5.", 1)[0])

    assert "kingmadoc explain scaffold" in step
    assert "one pass per document" in step and "not one edit per placeholder" in step


def test_wireframes_are_sketches_with_safe_grids() -> None:
    """A "design" is a Balsamiq-style sketch; grids always set rows and columns together."""
    stories = re.sub(r"\s+", " ", _read(FOLDER / "reference" / "stories.md"))

    assert "sketch: true" in stories and "never use screenshots" in stories
    assert "Always `grid-rows` and `grid-columns` together." in stories
    assert "`top` is reserved in D2" in stories
    assert "literally and in the same order" in stories
    source = _read(FOLDER / "reference" / "stories.md")
    for example in re.findall(r"```d2\n(.*?)\n```", source, re.S):
        for grid in re.findall(r"\{([^{}]*grid-(?:rows|columns)[^{}]*)", example):
            assert "grid-rows" in grid and "grid-columns" in grid, grid


def test_skill_examples_keep_arrow_labels_short_and_classes_readable() -> None:
    """Every D2 example passes render's label and class warnings (agents copy them)."""
    from kingmadoc.render import class_warnings, label_warnings

    for path in [SKILL, *sorted((FOLDER / "reference").glob("*.md"))]:
        for example in re.findall(r"^```d2\n(.*?)\n```$", _read(path), re.S | re.M):
            assert label_warnings(example) == [], (path.name, label_warnings(example))
            assert class_warnings(example) == [], path.name


def test_plain_language_and_tables_over_figures() -> None:
    """Mbo level in the user's language; a table when it is clearer than a figure."""
    rules = re.sub(r"\s+", " ", _read(SKILL))

    assert "secondary vocational (mbo) level" in rules and "idempotentie" in rules
    assert "Figures are not a goal" in rules
    assert "pip install --pre kingmadoc" in rules
    assert 'py -3 -c "from kingmadoc.cli import main; main()"' in rules
