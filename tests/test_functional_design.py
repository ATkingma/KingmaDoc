"""Tests for the optional functional design doc (``extra_designs.functional_design``)."""

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.config import FeatureDocConfig, parse_config
from kingmadoc.exceptions import ConfigError
from kingmadoc.threats.model import STATES

DESCRIPTION = "Add password reset via email. Links expire after 30 minutes."
FEATURES = Path("docs") / "features"
PLAN = FEATURES / "add-password-reset-via-email-plan.md"
FUNCTIONAL = FEATURES / "add-password-reset-via-email-functional-design.md"
TECHNICAL = FEATURES / "add-password-reset-via-email-technical-design.md"

SECTIONS = (
    "## User stories",
    "## Use case diagram",
    "## Per user story",
    "### US-1:",
    "#### Use case",
    "#### Screen design",
    "#### Evil user stories",
    "## User flows",
)


def _config(root: Path, functional: bool, technical: bool = False) -> None:
    (root / ".featuredoc.yml").write_text(
        "extra_designs:\n"
        f"  functional_design:\n    enabled: {str(functional).lower()}\n"
        f"  technical_design:\n    enabled: {str(technical).lower()}\n",
        encoding="utf-8",
    )


def _plan(root: Path, *extra: str) -> Result:
    return CliRunner().invoke(
        cli, ["plan", DESCRIPTION, "--root", str(root), "--no-input", *extra]
    )


def test_disabled_by_default(tmp_path: Path) -> None:
    """Without config, no functional design doc is written."""
    assert FeatureDocConfig().extra_designs.functional_design.enabled is False

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert not (tmp_path / FUNCTIONAL).exists()


def test_disabled_explicitly(tmp_path: Path) -> None:
    """``enabled: false`` behaves like the default."""
    _config(tmp_path, functional=False)

    assert _plan(tmp_path).exit_code == 0
    assert not (tmp_path / FUNCTIONAL).exists()


def test_enabled_writes_functional_design(tmp_path: Path) -> None:
    """When enabled, the doc is written next to the plan with all sections and a flowchart."""
    _config(tmp_path, functional=True)

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        str((tmp_path / PLAN).resolve()),
        str((tmp_path / FUNCTIONAL).resolve()),
    ]
    assert not (tmp_path / TECHNICAL).exists()
    doc = (tmp_path / FUNCTIONAL).read_text(encoding="utf-8")
    assert doc.startswith("# Functional design: Add password reset via email.\n")
    assert "[`add-password-reset-via-email-plan.md`](add-password-reset-via-email-plan.md)" in doc
    positions = [doc.find(section) for section in SECTIONS]
    assert -1 not in positions, [s for s, p in zip(SECTIONS, positions, strict=True) if p == -1]
    assert positions == sorted(positions)
    flows = doc[positions[SECTIONS.index("## User flows")]:]
    assert "```mermaid\nflowchart TD\n" in flows


def test_both_extra_designs(tmp_path: Path) -> None:
    """Functional (what) is written and printed before technical (how)."""
    _config(tmp_path, functional=True, technical=True)

    result = _plan(tmp_path)

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        str((tmp_path / path).resolve()) for path in (PLAN, FUNCTIONAL, TECHNICAL)
    ]
    printed = _plan(tmp_path, "--stdout")
    assert printed.exit_code == 0, printed.output
    stdout = printed.stdout
    assert (
        stdout.index("# Feature:")
        < stdout.index("# Functional design:")
        < stdout.index("# Technical design:")
    )


@pytest.mark.parametrize(
    "data",
    [
        {"extra_designs": {"functional_design": {"enabled": 1}}},
        {"extra_designs": {"functional_design": {"enabled": True, "templates": "x"}}},
        {"extra_designs": {"functional": {"enabled": True}}},
        {"extra_designs": {"functional_design": True}},
    ],
)
def test_invalid_config_raises(data: dict) -> None:
    """Typos and wrong types are rejected like every other config key."""
    with pytest.raises(ConfigError):
        parse_config(data)


def test_empty_entry_means_disabled() -> None:
    """``functional_design:`` with no value parses as disabled, not as an error."""
    config = parse_config({"extra_designs": {"functional_design": None}})

    assert config.extra_designs.functional_design.enabled is False


def _plan_with_requirements(root: Path) -> str:
    """Plan interactively; the acceptance answer gives two requirements."""
    answers = "\n\n\n\nA link is e-mailed; The link expires after 30 minutes\n"
    result = CliRunner().invoke(
        cli, ["plan", DESCRIPTION, "--root", str(root)], input=answers
    )
    assert result.exit_code == 0, result.output
    return (root / FUNCTIONAL).read_text(encoding="utf-8")


def test_red_thread_one_story_per_requirement(tmp_path: Path) -> None:
    """Each REQ-n gets a user story with its own use case, screen and evil user stories."""
    _config(tmp_path, functional=True)

    doc = _plan_with_requirements(tmp_path)

    assert "| US-1 | _TODO: role_ | _TODO: goal_ | _TODO: benefit_ | REQ-1 |" in doc
    assert "| US-2 | _TODO: role_ | _TODO: goal_ | _TODO: benefit_ | REQ-2 |" in doc
    assert "- **Covers:** REQ-2: The link expires after 30 minutes" in doc
    story_two = doc[doc.index("### US-2:"):doc.index("## User flows")]
    for part in ("| UC-2 | |", "S-2:", "| EUS-2.1 |", "#### Screen design"):
        assert part in story_two, part
    assert doc.count("### US-") == 2
    diagram = doc[doc.index("## Use case diagram"):doc.index("## Per user story")]
    assert 'uc1(["UC-1: TODO: goal"])' in diagram
    assert "user --> uc2" in diagram


def test_without_requirements_one_todo_story(tmp_path: Path) -> None:
    """With no acceptance criteria there is one story, linked to a REQ-n still to choose."""
    _config(tmp_path, functional=True)

    assert _plan(tmp_path).exit_code == 0

    doc = (tmp_path / FUNCTIONAL).read_text(encoding="utf-8")
    assert doc.count("### US-") == 1
    assert "- **Covers:** _TODO: REQ-n from the plan._" in doc


def test_threat_model_is_in_the_technical_design(tmp_path: Path) -> None:
    """Evil user stories point at security measures (SM-n) in the technical design.

    The threat model follows the Microsoft Threat Modeling Tool: STRIDE threats per
    interaction, with its states, a priority and a justification.
    """
    _config(tmp_path, functional=True, technical=True)
    assert _plan(tmp_path).exit_code == 0

    functional = (tmp_path / FUNCTIONAL).read_text(encoding="utf-8")
    technical = (tmp_path / TECHNICAL).read_text(encoding="utf-8")
    assert "## Threat model" not in functional
    assert "_TODO: SM-n (technical design)_" in functional
    threats = technical[technical.index("## Threat model"):]
    assert "| # | Threat | Category | Description | State | Priority | Justification |" in threats
    assert "| Spoofing the User External Entity | Spoofing |" in threats
    assert f"| {' | '.join(STATES)} | Total |" in threats
    assert "### Interaction: Request (User →" in threats
    assert "SDL TM Knowledge Base" in threats
    assert "| SM-1 |" in threats


@pytest.mark.parametrize(
    ("diagram_format", "expected"),
    [
        ("plantuml", 'usecase "UC-1: TODO: goal" as uc1'),
        ("d2", 'uc1: "UC-1: TODO: goal" {shape: oval}'),
    ],
)
def test_use_case_diagram_per_format(tmp_path: Path, diagram_format: str, expected: str) -> None:
    """The use case diagram is drawn in the configured diagram format."""
    (tmp_path / ".featuredoc.yml").write_text(
        f"diagram_format: {diagram_format}\n"
        "extra_designs:\n  functional_design:\n    enabled: true\n",
        encoding="utf-8",
    )
    assert _plan(tmp_path).exit_code == 0

    doc = (tmp_path / FUNCTIONAL).read_text(encoding="utf-8")
    diagram = doc[doc.index("## Use case diagram"):doc.index("## Per user story")]
    assert f"```{diagram_format}\n" in diagram
    assert expected in diagram


def test_every_model_is_on_by_default() -> None:
    """User stories, use cases, screens, evil user stories … all switched on."""
    assert FeatureDocConfig().extra_designs.functional_design.models == (
        "user_stories", "use_case_diagram", "use_cases", "screen_designs",
        "evil_user_stories", "user_flows",
    )


def test_config_can_switch_models_off(tmp_path: Path) -> None:
    """Only the chosen models are written; no empty sections remain."""
    (tmp_path / ".featuredoc.yml").write_text(
        "extra_designs:\n  functional_design:\n    enabled: true\n"
        "    models: [user_stories, evil_user_stories]\n",
        encoding="utf-8",
    )
    assert _plan(tmp_path).exit_code == 0

    doc = (tmp_path / FUNCTIONAL).read_text(encoding="utf-8")
    assert "## User stories" in doc and "#### Evil user stories" in doc
    for gone in ("## Use case diagram", "#### Use case\n", "#### Screen design",
                 "## User flows"):
        assert gone not in doc, gone
    assert "\n\n\n" not in doc


def test_models_option_picks_models_and_their_documents(tmp_path: Path) -> None:
    """`--models` (e.g. from the agent's prompt) switches on just the docs that have them."""
    result = _plan(tmp_path, "--models", "screen_designs,threat_model")

    assert result.exit_code == 0, result.output
    names = sorted(Path(line).name for line in result.stdout.splitlines())
    assert names == sorted([PLAN.name, FUNCTIONAL.name, TECHNICAL.name,
                            "add-password-reset-via-email-security-design.md"])
    functional = (tmp_path / FUNCTIONAL).read_text(encoding="utf-8")
    assert "#### Screen design" in functional and "## User stories" not in functional
    technical = (tmp_path / TECHNICAL).read_text(encoding="utf-8")
    assert "## Threat model" in technical and "## Dependency graph" not in technical


def test_models_option_rejects_unknown_names(tmp_path: Path) -> None:
    result = _plan(tmp_path, "--models", "threat_modle")

    assert result.exit_code == 1 and "Unknown model 'threat_modle'" in result.output


def test_functional_design_is_for_stakeholders(tmp_path: Path) -> None:
    """The FO has no technical parts: rules, permissions and edge cases are in the TO."""
    _config(tmp_path, functional=True, technical=True)
    assert _plan(tmp_path).exit_code == 0

    functional = (tmp_path / FUNCTIONAL).read_text(encoding="utf-8")
    technical = (tmp_path / TECHNICAL).read_text(encoding="utf-8")
    for section in ("## Business rules", "## Permissions and roles", "## Edge cases",
                    "## Threat model"):
        assert section not in functional, section
        assert section in technical, section
    assert "For stakeholders" in functional and "For developers" in technical


@pytest.mark.parametrize(("documents", "written"), [
    ("single", [PLAN]),
    ("split", [PLAN, FUNCTIONAL, TECHNICAL]),
    ("functional", [PLAN, FUNCTIONAL]),
    ("technical", [PLAN, TECHNICAL]),
])
def test_documents_option_picks_fo_and_to(
    tmp_path: Path, documents: str, written: list[Path]
) -> None:
    """Only the plan by default; "make an FO and TO" is `--documents split`."""
    _config(tmp_path, functional=documents == "single", technical=False)

    result = _plan(tmp_path, "--documents", documents)

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [str((tmp_path / p).resolve()) for p in written]


def test_the_plan_skill_splits_on_request() -> None:
    """The skill maps "FO/TO", "functional and technical design", "split" to both docs."""
    skill = (Path(__file__).resolve().parents[1] / "skill" / "SKILL.md").read_text(
        encoding="utf-8")
    text = " ".join(skill.split())

    assert "By default only the plan is written" in text
    for phrase in ('"FO/TO"', '"functional and technical design"', '"split" → both',
                   '"only an FO"', '"only a TO"', "--documents split"):
        assert phrase in text, phrase
