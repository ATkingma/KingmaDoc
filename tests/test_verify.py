"""Tests for `kingmadoc verify` (roadmap WP2): the code compared with its plan.

A small git repository gets a plan and then an implementation with planted
deviations: an expected file never touched, a change outside the plan, a requirement
no test or commit mentions, and a new container.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.plandoc import parse_plan
from kingmadoc.verify.changes import Changes
from kingmadoc.verify.commands import CheckCommand, detect_commands, run_check
from kingmadoc.verify.deviations import find_deviations

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

PLAN = """\
---
kingmadoc: 1
feature: cancel-order
status: {status}
requirements: [REQ-1, REQ-2]
files_expected: [shop/services.py, shop/views.py]
---
# Feature: Cancel an order

| | |
|---|---|
| **Project** | shop |
| **Status** | {status_title} |
| **Generated** | 2026-02-01T12:00+00:00 by KingmaDoc test |

## Requirements

- **REQ-1**: WHEN a customer cancels a new order THE SYSTEM SHALL mark it cancelled.
- **REQ-2**: WHEN an order is cancelled THE SYSTEM SHALL return its stock.

## C4 Container (Mermaid)

```mermaid
C4Container
    Container(shop, "shop", "Python", "Source module shop/")
```
"""


def _git(root: Path, *args: str, date: str | None = None) -> str:
    env = {**os.environ}
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True, env=env
    ).stdout.strip()


def _write(root: Path, name: str, text: str) -> None:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text, encoding="utf-8")


def _repo(tmp_path: Path, status: str = "approved") -> Path:
    """Before the plan: shop/. After it: views changed, a new worker/, REQ-1 in a test."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    for name in ("shop/services.py", "shop/views.py", "shop/models.py"):
        _write(tmp_path, name, "x = 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "Shop", date="2026-01-01T12:00:00+00:00")
    _write(tmp_path, "docs/features/cancel-order-plan.md",
           PLAN.format(status=status, status_title=status.capitalize()))
    _write(tmp_path, "shop/views.py", "def cancel(): ...\n")
    _write(tmp_path, "worker/jobs.py", "def refund(): ...\n")
    _write(tmp_path, "tests/test_cancel.py", "def test_cancel():  # REQ-1\n    pass\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "Cancel orders", date="2026-03-01T12:00:00+00:00")
    _write(tmp_path, "shop/models.py", "x = 2\n")  # uncommitted, outside the plan
    return tmp_path


def _verify(root: Path, *extra: str) -> Result:
    return CliRunner().invoke(cli, ["verify", "cancel-order", "--root", str(root), *extra])


def _doc(root: Path) -> str:
    return (root / "docs" / "features" / "cancel-order-verify.md").read_text(encoding="utf-8")


@needs_git
def test_verify_reports_the_planted_deviations(tmp_path: Path) -> None:
    """Untouched expected file, change outside the plan, unmentioned REQ, new container."""
    root = _repo(tmp_path)

    result = _verify(root)

    assert result.exit_code == 0, result.output
    doc = _doc(root)
    assert doc.startswith("# Verification: cancel-order\n")
    assert "| **Status** | Deviations found |" in doc
    assert "`shop/services.py`" in doc and "not changed" in doc
    assert "`shop/models.py`" in doc and "`worker/jobs.py`" in doc
    assert "REQ-2" in doc and "no test or commit mentions REQ-2" in doc
    assert "REQ-1" not in doc.split("## Deviations", 1)[1].split("## Validation", 1)[0]
    assert "`worker`" in doc and "not in the plan's container diagram" in doc
    assert "docs/features" not in doc.split("## Deviations", 1)[1]


@needs_git
def test_verify_sets_the_plan_status(tmp_path: Path) -> None:
    """Deviations found: the approved plan becomes partial."""
    root = _repo(tmp_path)

    assert _verify(root).exit_code == 0
    plan = (root / "docs" / "features" / "cancel-order-plan.md").read_text(encoding="utf-8")

    assert parse_plan(plan).status == "partial"
    assert "| **Status** | Partial |" in plan


@needs_git
def test_a_draft_plan_is_a_process_deviation_and_stays_draft(tmp_path: Path) -> None:
    """Code written before approval breaks the gate; the plan is not marked implemented."""
    root = _repo(tmp_path, status="draft")

    assert _verify(root).exit_code == 0

    assert "still draft" in _doc(root)
    plan = (root / "docs" / "features" / "cancel-order-plan.md").read_text(encoding="utf-8")
    assert parse_plan(plan).status == "draft"


@needs_git
def test_checks_run_only_with_the_flag(tmp_path: Path) -> None:
    """Commands from the repository never run without --run-checks."""
    root = _repo(tmp_path)
    marker = root / "ran.txt"
    command = f"{sys.executable} -c \"open(r'{marker}', 'w').write('x')\""
    _write(root, ".featuredoc.yml", f"verify:\n  test: {json.dumps(command)}\n")

    without = _verify(root, "--force")
    ran_without, doc_without = marker.exists(), _doc(root)
    with_flag = _verify(root, "--force", "--run-checks")

    assert without.exit_code == 0 and not ran_without
    assert "_not run_" in doc_without and "--run-checks" in doc_without
    assert with_flag.exit_code == 0, with_flag.output
    assert marker.exists()
    assert "| Tests |" in _doc(root) and "passed" in _doc(root)


@needs_git
def test_a_failing_check_is_a_finding(tmp_path: Path) -> None:
    """A failing test command is shown with the end of its output."""
    root = _repo(tmp_path)
    command = f"{sys.executable} -c \"import sys; print('1 failed'); sys.exit(1)\""
    _write(root, ".featuredoc.yml", f"verify:\n  test: {json.dumps(command)}\n")

    result = _verify(root, "--run-checks")

    assert result.exit_code == 0, result.output
    assert "failed" in _doc(root) and "1 failed" in _doc(root)


def test_a_plan_without_frontmatter_is_not_verified(tmp_path: Path) -> None:
    """Plans from before WP1 still verify; the result says what is missing."""
    path = tmp_path / "docs" / "features" / "cancel-order-plan.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Feature: Cancel an order\n", encoding="utf-8")

    result = _verify(tmp_path)

    assert result.exit_code == 0, result.output
    doc = _doc(tmp_path)
    assert "| **Status** | Not verified |" in doc
    assert "frontmatter" in doc


def test_detect_commands_per_ecosystem() -> None:
    """Project files name the build, test and lint commands; config wins."""
    npm = detect_commands({"package.json": '{"scripts": {"build": "tsc", "test": "vitest"}}'})
    python = detect_commands({"pyproject.toml": "[tool.ruff]\n[tool.pytest.ini_options]\n"})
    dotnet = detect_commands({"Shop.sln": ""})
    make = detect_commands({"Makefile": "build:\n\tgo build\ntest:\n\tgo test\n", "go.mod": ""})
    configured = detect_commands({"Makefile": "test:\n\tx\n"}, {"test": "tox"})

    assert npm == (CheckCommand("Build", "npm run build", "package.json"),
                   CheckCommand("Tests", "npm test", "package.json"))
    assert [c.command for c in python] == ["pytest", "ruff check ."]
    assert [c.command for c in dotnet] == ["dotnet build", "dotnet test"]
    assert [c.command for c in make] == ["make build", "make test", "go vet ./..."]
    assert configured == (CheckCommand("Tests", "tox", ".featuredoc.yml"),)


def test_run_check_reports_a_missing_program(tmp_path: Path) -> None:
    """A command that does not exist fails with a clear reason instead of crashing."""
    result = run_check(tmp_path, CheckCommand("Tests", "no-such-program-xyz", "x"), timeout=5)

    assert result.passed is False and "not found" in result.detail


def test_find_deviations_without_expected_files() -> None:
    """With files_expected empty, changed files cannot be outside the plan."""
    meta = parse_plan(PLAN.format(status="approved", status_title="Approved").replace(
        "[shop/services.py, shop/views.py]", "[]"))
    changes = Changes(base="abc1234", files=("shop/x.py",), messages="REQ-1 REQ-2", problem=None)

    found = find_deviations(meta, changes, frozenset({"REQ-1", "REQ-2"}), ("shop",), ("shop",))

    assert found == ()


def test_generated_time_is_read_from_the_plan() -> None:
    """The comparison starts at the plan's **Generated** time."""
    from kingmadoc.plandoc import generated_at

    when = generated_at(PLAN.format(status="draft", status_title="Draft"))

    assert when == datetime.fromisoformat("2026-02-01T12:00+00:00")


@needs_git
def test_a_plan_written_right_after_a_commit(tmp_path: Path) -> None:
    """Generated is to the minute: a commit in the same minute is still before the plan."""
    root = tmp_path
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "T")
    _git(root, "config", "commit.gpgsign", "false")
    for name in ("shop/services.py", "shop/views.py"):
        _write(root, name, "x = 1\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "Shop")
    answers = "\n".join(["", "", "", "shop/services.py", "Orders can be cancelled"]) + "\n"
    planned = CliRunner().invoke(cli, ["plan", "Cancel an order.", "--root", str(root)],
                                 input=answers)
    assert planned.exit_code == 0, planned.output
    _write(root, "shop/services.py", "def cancel(): ...\n")

    result = CliRunner().invoke(cli, ["verify", "cancel-an-order", "--root", str(root)])

    assert result.exit_code == 0, result.output
    doc = (root / "docs" / "features" / "cancel-an-order-verify.md").read_text("utf-8")
    assert "1 file changed since the plan" in doc
    assert "also changed" not in doc

