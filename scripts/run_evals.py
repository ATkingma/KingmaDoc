"""Run the skill evaluations in evals/: does an agent follow the KingmaDoc skills?

Each scenario (evals/scenarios/*.yml) copies a fixture project into a temporary git
repository, optionally makes a branch, installs the skills (or not, for the baseline),
gives an agent the request, and checks the result. The checks are deterministic: files
in the right place, the format's headings, pictures instead of D2 source, at most three
questions, no source code changed.

    python scripts/run_evals.py                        # all scenarios, with the skills
    python scripts/run_evals.py --compare              # with and without, side by side
    python scripts/run_evals.py explain-feature --record   # save to evals/results/
    python scripts/run_evals.py plan-feature --check-only DIR  # only check a workspace

The agent is Claude Code by default (``claude -p``, Bash limited to kingmadoc, git and
ls); ``--agent`` takes any command with ``{request}`` in it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from kingmadoc.plandoc import check_plan

REPO = Path(__file__).resolve().parents[1]
EVALS = REPO / "evals"
AGENT_TIMEOUT = 45 * 60
# How much of the agent's final reply is recorded (its end: the question it stopped on).
REPLY_CHARS = 600
ALLOWED_TOOLS = ",".join([
    "Read", "Write", "Edit", "Glob", "Grep", "Skill",
    "Bash(kingmadoc:*)", "Bash(git log:*)", "Bash(git diff:*)", "Bash(git status:*)",
    "Bash(git show:*)", "Bash(git branch:*)", "Bash(git rev-parse:*)", "Bash(ls:*)",
])
DEFAULT_AGENT = (
    "claude -p {request} --output-format json --max-turns 80 "
    f"--allowedTools {shlex.quote(ALLOWED_TOOLS)}"
)
QUESTIONS_HEADING = re.compile(r"^#{2,3} .*(?:Couldn't work out|Open questions).*$", re.M | re.I)

Check = Callable[[Path, Any], tuple[bool, str]]


# --- checks ----------------------------------------------------------------------------


def check_exists(workspace: Path, pattern: str) -> tuple[bool, str]:
    """At least one file matches the glob."""
    found = sorted(workspace.glob(pattern))
    return bool(found), ", ".join(_rel(workspace, p) for p in found) or f"nothing at {pattern}"


def check_contains(workspace: Path, spec: dict[str, Any]) -> tuple[bool, str]:
    """Every matching file contains every text (case-insensitive)."""
    files = sorted(workspace.glob(spec["files"]))
    if not files:
        return False, f"nothing at {spec['files']}"
    missing = [
        f"{_rel(workspace, f)}: {text!r}"
        for f in files
        for text in spec["text"]
        if text.lower() not in f.read_text(encoding="utf-8", errors="replace").lower()
    ]
    return not missing, "; ".join(missing) or "all present"


def check_pictures_only(workspace: Path, pattern: str) -> tuple[bool, str]:
    """No D2 source left in the documents, and every image they show exists.

    Text is fine; what may not stay is a ```d2 block that was never rendered.
    """
    files = sorted(workspace.glob(pattern))
    if not files:
        return False, f"nothing at {pattern}"
    problems, images = [], 0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        if "```d2" in text:
            problems.append(f"{_rel(workspace, f)}: D2 source not rendered")
        for target in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", text):
            images += 1
            if "://" not in target and not (f.parent / target).is_file():
                problems.append(f"{_rel(workspace, f)}: missing image {target}")
    if not images:
        problems.append("no images")
    return not problems, "; ".join(problems) or f"{images} images"


def check_max_questions(workspace: Path, spec: dict[str, Any]) -> tuple[bool, str]:
    """The questions section has at most ``max`` bullets (or is absent)."""
    counts = []
    for f in sorted(workspace.glob(spec["files"])):
        text = f.read_text(encoding="utf-8", errors="replace")
        heading = QUESTIONS_HEADING.search(text)
        if heading:
            section = re.split(r"^#{1,3} ", text[heading.end():], maxsplit=1, flags=re.M)[0]
            counts.append(len(re.findall(r"^\s*[-*] \S", section, re.M)))
    worst = max(counts, default=0)
    return worst <= spec["max"], f"{worst} question(s)"


def check_unchanged_outside(workspace: Path, allowed: list[str]) -> tuple[bool, str]:
    """git sees no change outside the allowed paths (no source code touched)."""
    status = _git(workspace, "status", "--porcelain", "--untracked-files=all")
    changed = [line[3:].strip('"') for line in status.splitlines() if line.strip()]
    outside = [p for p in changed if not p.startswith(tuple(allowed))]
    return not outside, ", ".join(outside) or f"{len(changed)} change(s), all allowed"


def check_plan_check(workspace: Path, pattern: str) -> tuple[bool, str]:
    """Every matching plan passes `kingmadoc check` (frontmatter and REQ IDs)."""
    files = sorted(workspace.glob(pattern))
    if not files:
        return False, f"nothing at {pattern}"
    problems = [
        f"{_rel(workspace, f)}: {problem}"
        for f in files
        for problem in check_plan(f.read_text(encoding="utf-8", errors="replace"),
                                  slug=f.name.removesuffix("-plan.md"))
    ]
    return not problems, "; ".join(problems) or "valid"


CHECKS: dict[str, Check] = {
    "exists": check_exists,
    "contains": check_contains,
    "pictures_only": check_pictures_only,
    "max_questions": check_max_questions,
    "unchanged_outside": check_unchanged_outside,
    "plan_check": check_plan_check,
}


def run_checks(workspace: Path, checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run a scenario's checks on a workspace.

    Args:
        workspace: The project after the agent ran.
        checks: The scenario's ``checks`` list (one ``{name: argument}`` each).

    Returns:
        One ``{"check", "ok", "detail"}`` per check.
    """
    results = []
    for item in checks:
        ((name, argument),) = item.items()
        ok, detail = CHECKS[name](workspace, argument)
        results.append({"check": f"{name} {_short(argument)}", "ok": ok, "detail": detail})
    return results


# --- scenarios -------------------------------------------------------------------------


def load_scenarios(names: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """Read evals/scenarios/*.yml, optionally only the named ones."""
    scenarios = {
        path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted((EVALS / "scenarios").glob("*.yml"))
    }
    unknown = set(names or ()) - set(scenarios)
    if unknown:
        raise SystemExit(f"unknown scenario(s): {', '.join(sorted(unknown))}")
    return {k: v for k, v in scenarios.items() if not names or k in names}


def prepare_workspace(scenario: dict[str, Any], target: Path, with_skills: bool) -> None:
    """Copy the fixture into ``target`` as a git repository, with the branch and skills."""
    shutil.copytree(EVALS / "fixtures" / scenario["fixture"], target, dirs_exist_ok=True)
    _git(target, "init", "-q", "-b", "main")
    for key, value in (("user.email", "eval@example.com"), ("user.name", "Eval"),
                       ("commit.gpgsign", "false")):
        _git(target, "config", key, value)
    _git(target, "add", ".")
    _git(target, "commit", "-qm", "Fixture")
    branch = scenario.get("branch")
    if branch:
        _git(target, "checkout", "-qb", branch["name"])
        shutil.copytree(EVALS / "fixtures" / branch["overlay"], target, dirs_exist_ok=True)
        _git(target, "add", ".")
        _git(target, "commit", "-qm", f"Work on {branch['name']}")
    if with_skills:
        subprocess.run(
            [_kingmadoc(), "skills", "install", "--root", str(target)],
            check=True, capture_output=True,
        )
        # The skills are part of the setup, not a change by the agent.
        _git(target, "add", ".")
        _git(target, "commit", "-qm", "Install KingmaDoc skills")


def run_agent(workspace: Path, request: str, agent: str) -> dict[str, Any]:
    """Run the agent command in the workspace; kingmadoc from this checkout is on PATH."""
    command = [request if part == "{request}" else part for part in shlex.split(agent)]
    env = {**os.environ, "PATH": f"{Path(_kingmadoc()).parent}{os.pathsep}{os.environ['PATH']}"}
    started = time.monotonic()
    try:
        done = subprocess.run(
            command, cwd=workspace, env=env, capture_output=True, text=True,
            timeout=AGENT_TIMEOUT, check=False,
        )
        output, errors, code = done.stdout, done.stderr, done.returncode
    except subprocess.TimeoutExpired:
        output, errors, code = "", f"timed out after {AGENT_TIMEOUT} s", -1
    info: dict[str, Any] = {"exit_code": code, "seconds": round(time.monotonic() - started)}
    data: dict[str, Any] = {}
    try:
        loaded = json.loads(output)
        data = loaded if isinstance(loaded, dict) else {}
    except (json.JSONDecodeError, TypeError):
        pass
    info.update({k: data[k] for k in ("total_cost_usd", "num_turns") if k in data})
    if isinstance(data.get("result"), str):
        info["reply"] = data["result"][-REPLY_CHARS:]
    # Tell an agent that failed (limits, max turns, crash) apart from a skill that failed.
    if data.get("is_error") or code != 0:
        tail = [line.strip() for line in errors.splitlines() if line.strip()][-1:]
        info["error"] = str(data.get("subtype") or "") if data.get("is_error") else ""
        info["error"] = info["error"] or (tail[0] if tail else f"exit code {code}")
    return info


def run_scenario(
    name: str, scenario: dict[str, Any], agent: str, with_skills: bool, keep: Path | None
) -> dict[str, Any]:
    """Prepare a workspace, run the agent, check the result."""
    with tempfile.TemporaryDirectory(prefix=f"kingmadoc-eval-{name}-") as tmp:
        workspace = Path(tmp) / "project"
        prepare_workspace(scenario, workspace, with_skills)
        agent_info = run_agent(workspace, scenario["request"], agent)
        checks = run_checks(workspace, scenario["checks"])
        if keep:
            destination = keep / f"{name}-{'skill' if with_skills else 'baseline'}"
            shutil.rmtree(destination, ignore_errors=True)
            shutil.copytree(workspace, destination)
    return {
        "scenario": name,
        "variant": "with skill" if with_skills else "without skill",
        "agent": agent_info,
        "checks": checks,
        "passed": sum(c["ok"] for c in checks),
        "total": len(checks),
    }


# --- reporting -------------------------------------------------------------------------


def summary(results: list[dict[str, Any]]) -> str:
    """A plain-text table: scenario, variant, passed checks, and each failure."""
    lines = []
    for r in results:
        cost = r["agent"].get("total_cost_usd")
        extra = f", ${cost:.2f}" if isinstance(cost, int | float) else ""
        lines.append(
            f"{r['scenario']} ({r['variant']}): {r['passed']}/{r['total']} checks"
            f" ({r['agent']['seconds']} s{extra})"
        )
        if r["agent"].get("error"):
            lines.append(f"  AGENT ERROR: {r['agent']['error']}")
        lines += [f"  FAIL {c['check']}: {c['detail']}" for c in r["checks"] if not c["ok"]]
        if r["passed"] < r["total"] and r["agent"].get("reply"):
            lines.append(f"  REPLY (end): {' '.join(r['agent']['reply'].split())[-200:]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("scenarios", nargs="*", help="Scenario names (default: all).")
    parser.add_argument("--agent", default=DEFAULT_AGENT, help="Command, with {request}.")
    parser.add_argument("--compare", action="store_true", help="Also run without skills.")
    parser.add_argument("--without-skill", action="store_true", help="Only the baseline.")
    parser.add_argument("--record", action="store_true", help="Save to evals/results/.")
    parser.add_argument("--repeat", type=int, default=1, metavar="N",
                        help="Run each scenario N times (agents vary between runs).")
    parser.add_argument("--keep", type=Path, help="Copy each final workspace here.")
    parser.add_argument("--check-only", type=Path, metavar="DIR",
                        help="Only run the checks of one scenario on DIR.")
    args = parser.parse_args(argv)

    scenarios = load_scenarios(args.scenarios)
    if args.check_only:
        if len(scenarios) != 1:
            parser.error("--check-only needs exactly one scenario")
        ((name, scenario),) = scenarios.items()
        checks = run_checks(args.check_only, scenario["checks"])
        result = {"scenario": name, "variant": "checked", "agent": {"seconds": 0},
                  "checks": checks, "passed": sum(c["ok"] for c in checks), "total": len(checks)}
        print(summary([result]))
        return 0 if result["passed"] == result["total"] else 1

    variants = [False] if args.without_skill else [True, False] if args.compare else [True]
    results = [
        run_scenario(name, scenario, args.agent, with_skills, args.keep)
        for name, scenario in scenarios.items()
        for with_skills in variants
        for _ in range(max(args.repeat, 1))
    ]
    print(summary(results))
    if args.record:
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
        path = EVALS / "results" / f"{stamp}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"agent": args.agent, "results": results}, indent=2) + "\n",
                        encoding="utf-8")
        print(f"Recorded in {path.relative_to(REPO)}")
    with_skill = [r for r in results if r["variant"] == "with skill"]
    return 0 if all(r["passed"] == r["total"] for r in with_skill) else 1


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout


def _kingmadoc() -> str:
    """The kingmadoc of this checkout's environment (the one being evaluated)."""
    name = "kingmadoc.exe" if os.name == "nt" else "kingmadoc"
    local = Path(sys.executable).parent / name
    return str(local) if local.is_file() else (shutil.which("kingmadoc") or "kingmadoc")


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _short(argument: Any) -> str:
    if isinstance(argument, dict):
        return str(argument.get("files", ""))
    if isinstance(argument, list):
        return "[" + ", ".join(map(str, argument)) + "]"
    return str(argument)


if __name__ == "__main__":
    raise SystemExit(main())
