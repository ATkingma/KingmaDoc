"""Tests for the skill evaluations (roadmap WP5): scenarios, checks and the runner.

The agent itself is not run here (that costs a real agent session); a fake agent that
writes a good or a bad result stands in for it.
"""

import importlib.util
import shlex
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from kingmadoc.skills import SKILL_NAMES

REPO = Path(__file__).resolve().parents[1]
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_evals", REPO / "scripts" / "run_evals.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evals = _runner()

GOOD_EXPLAINER = """\
# Placing an order: architecture explained

| | |
| --- | --- |
| **Based on** | abc1234 · 2026-09-27 · KingmaDoc skill explaining-code |

## What changed

The discount.

## 1. Introduction and goals

<!-- kingmadoc:diagram img/figure-1.d2 -->
![Context](img/figure-1.svg)

## 5. Building block view
## 6. Runtime view
## 8. Cross-cutting concepts

## Couldn't work out

- Who ships orders?
"""

# Writes the explainer (argv[1] is the request) into the current directory.
FAKE_AGENT = """\
import pathlib, sys
folder = pathlib.Path("docs/explain/0001-orders")
(folder / "img").mkdir(parents=True)
text = pathlib.Path(sys.argv[2]).read_text()
(folder / "README.md").write_text(text)
(folder / "img" / "figure-1.svg").write_text("<svg/>")
pathlib.Path("docs/explain/README.md").write_text("# Explained code\\n")
if "BREAK" in sys.argv[1]:
    pathlib.Path("shop/models.py").write_text("changed")
"""


def test_every_scenario_is_valid() -> None:
    """At least three scenarios; known skill, fixture and check names."""
    scenarios = evals.load_scenarios()

    assert len(scenarios) >= 3
    for name, scenario in scenarios.items():
        assert scenario["skill"] in SKILL_NAMES, name
        assert (REPO / "evals" / "fixtures" / scenario["fixture"]).is_dir(), name
        assert scenario["request"].strip(), name
        if "branch" in scenario:
            assert (REPO / "evals" / "fixtures" / scenario["branch"]["overlay"]).is_dir(), name
        for check in scenario["checks"]:
            ((check_name, _),) = check.items()
            assert check_name in evals.CHECKS, f"{name}: {check_name}"
        assert any("unchanged_outside" in c for c in scenario["checks"]), name


def _workspace(tmp_path: Path, explainer: str) -> Path:
    folder = tmp_path / "docs" / "explain" / "0001-orders"
    (folder / "img").mkdir(parents=True)
    (folder / "README.md").write_text(explainer, encoding="utf-8")
    (folder / "img" / "figure-1.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "docs" / "explain" / "README.md").write_text("# Index\n", encoding="utf-8")
    return tmp_path


def test_checks_pass_on_a_good_explainer(tmp_path: Path) -> None:
    """The file checks accept an explainer that follows the skill."""
    workspace = _workspace(tmp_path, GOOD_EXPLAINER)
    checks = [
        c for c in evals.load_scenarios(["explain-feature"])["explain-feature"]["checks"]
        if "unchanged_outside" not in c
    ]

    results = evals.run_checks(workspace, checks)

    assert all(r["ok"] for r in results), results


@pytest.mark.parametrize(
    ("change", "failing"),
    [
        (lambda t: t.replace("![Context](img/figure-1.svg)", "```d2\na -> b\n```"),
         "pictures_only"),
        (lambda t: t.replace("figure-1.svg", "figure-9.svg"), "pictures_only"),
        (lambda t: t + "- a?\n- b?\n- c?\n", "max_questions"),
        (lambda t: t.replace("## 6. Runtime view", ""), "contains"),
    ],
)
def test_checks_catch_a_bad_explainer(
    tmp_path: Path, change: Callable[[str], str], failing: str
) -> None:
    """Unrendered D2, a missing image, too many questions, a missing heading."""
    workspace = _workspace(tmp_path, change(GOOD_EXPLAINER))
    checks = evals.load_scenarios(["explain-feature"])["explain-feature"]["checks"]

    results = evals.run_checks(workspace, [c for c in checks if "unchanged_outside" not in c])

    failed = {r["check"].split()[0] for r in results if not r["ok"]}
    assert failed == {failing}


@needs_git
def test_workspace_has_the_branch_and_the_skills(tmp_path: Path) -> None:
    """The branch scenario gets its branch commit; the skills are committed as setup."""
    scenario = evals.load_scenarios(["explain-branch"])["explain-branch"]
    workspace = tmp_path / "project"

    evals.prepare_workspace(scenario, workspace, with_skills=True)

    git = ["git", "-C", str(workspace)]
    branch = subprocess.run([*git, "branch", "--show-current"], capture_output=True, text=True)
    status = subprocess.run([*git, "status", "--porcelain"], capture_output=True, text=True)
    assert branch.stdout.strip() == "feature/discount"
    assert (workspace / "shop" / "discounts.py").is_file()
    assert (workspace / ".claude" / "skills" / "explaining-code" / "SKILL.md").is_file()
    assert status.stdout == ""


@needs_git
@pytest.mark.parametrize(("request_text", "passes"), [("Explain", True), ("Explain BREAK", False)])
def test_run_scenario_with_a_fake_agent(tmp_path: Path, request_text: str, passes: bool) -> None:
    """End to end: the agent's result is checked, and changed source code fails."""
    agent_script = tmp_path / "agent.py"
    agent_script.write_text(FAKE_AGENT, encoding="utf-8")
    explainer = tmp_path / "explainer.md"
    explainer.write_text(GOOD_EXPLAINER, encoding="utf-8")
    scenario = {**evals.load_scenarios(["explain-feature"])["explain-feature"],
                "request": request_text}
    # Quoted: shlex would drop the backslashes of Windows paths.
    python, script, doc = (shlex.quote(str(p)) for p in (sys.executable, agent_script, explainer))
    agent = f"{python} {script} {{request}} {doc}"

    result = evals.run_scenario("explain-feature", scenario, agent, True, None)

    assert (result["passed"] == result["total"]) is passes, evals.summary([result])
    assert result["agent"]["exit_code"] == 0


def test_summary_lists_failures() -> None:
    """The report names each failing check with its detail."""
    text = evals.summary([{
        "scenario": "s", "variant": "with skill", "agent": {"seconds": 3, "total_cost_usd": 0.5},
        "checks": [{"check": "exists x", "ok": False, "detail": "nothing at x"}],
        "passed": 0, "total": 1,
    }])

    assert text == "s (with skill): 0/1 checks (3 s, $0.50)\n  FAIL exists x: nothing at x"


def test_fixture_is_valid_python() -> None:
    """The fixture code compiles (agents read it; it is never run)."""
    for path in (REPO / "evals" / "fixtures").rglob("*.py"):
        compile(textwrap.dedent(path.read_text(encoding="utf-8")), str(path), "exec")
