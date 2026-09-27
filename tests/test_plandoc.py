"""Tests for machine-readable plans (roadmap WP1): frontmatter, REQ IDs, check, approve."""

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.plandoc import check_plan, parse_plan, set_status

VALID = """\
---
kingmadoc: 1
feature: password-reset
status: draft
requirements: [REQ-1, REQ-2]
files_expected: [src/auth/reset.py]
---
# Feature: Password reset

| | |
|---|---|
| **Status** | Draft |

## Requirements

- **REQ-1**: WHEN a user requests a reset THE SYSTEM SHALL email a single-use link.
- **REQ-2**: IF the link is older than 30 minutes THEN THE SYSTEM SHALL reject it.
"""


def _plan(root: Path, text: str, slug: str = "password-reset") -> Path:
    path = root / "docs" / "features" / f"{slug}-plan.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _run(root: Path, *args: str) -> Result:
    return CliRunner().invoke(cli, [*args, "--root", str(root)])


def test_a_valid_plan_parses() -> None:
    """The frontmatter becomes typed metadata."""
    meta = parse_plan(VALID)

    assert meta.feature == "password-reset"
    assert meta.status == "draft"
    assert meta.requirements == ("REQ-1", "REQ-2")
    assert meta.files_expected == ("src/auth/reset.py",)
    assert check_plan(VALID, slug="password-reset") == []


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda t: t.split("---\n", 2)[2], "no frontmatter"),
        (lambda t: t.replace("status: draft", "status: done"), "status"),
        (lambda t: t.replace("kingmadoc: 1", "kingmadoc: 2"), "format version"),
        (lambda t: t.replace("[REQ-1, REQ-2]", "[REQ-1]"), "REQ-2"),
        (lambda t: t.replace("[REQ-1, REQ-2]", "[REQ-1, REQ-2, REQ-3]"), "REQ-3"),
        (lambda t: t.replace("[REQ-1, REQ-2]", "[REQ-1, REQ-1, REQ-2]"), "twice"),
        (lambda t: t.replace("[REQ-1, REQ-2]", "[REQ-1, R2]"), "R2"),
        (lambda t: t.replace("feature: password-reset", "feature: other"), "other"),
        (lambda t: t.replace("files_expected:", "owner: me\nfiles_expected:"), "owner"),
        (lambda t: t.replace("[src/auth/reset.py]", "[../etc/passwd]"), "../etc/passwd"),
        (lambda t: t.replace("status: draft", "status: [draft"), "YAML"),
    ],
)
def test_broken_plans_fail_with_a_useful_message(
    change: Callable[[str], str], message: str
) -> None:
    """Every problem is reported in words that point at the fix."""
    problems = check_plan(change(VALID), slug="password-reset")

    assert problems, "expected a problem"
    assert any(message in p for p in problems), problems


def test_set_status_changes_the_frontmatter_and_the_table() -> None:
    """Approving updates both places a human or a tool reads the status."""
    text = set_status(VALID, "approved")

    assert parse_plan(text).status == "approved"
    assert "| **Status** | Approved |" in text
    assert text.replace("approved", "draft").replace("Approved", "Draft") == VALID


def test_generated_plan_passes_check(tmp_path: Path) -> None:
    """`plan` writes frontmatter, a Requirements section and REQ IDs that `check` accepts."""
    written = _run(tmp_path, "plan", "Add password reset via email.", "--no-input")
    assert written.exit_code == 0, written.output
    path = Path(written.output.strip().splitlines()[0])
    text = path.read_text(encoding="utf-8")

    result = _run(tmp_path, "check", "add-password-reset-via-email")

    assert result.exit_code == 0, result.output
    assert "draft" in result.output and "1 requirement" in result.output
    meta = yaml.safe_load(text.split("---\n", 2)[1])
    assert meta == {
        "kingmadoc": 1, "feature": "add-password-reset-via-email", "status": "draft",
        "requirements": ["REQ-1"], "files_expected": [],
    }
    assert "- **REQ-1**: _TODO: WHEN <trigger> THE SYSTEM SHALL <response>._" in text


def test_answers_fill_requirements_and_expected_files(tmp_path: Path) -> None:
    """Acceptance criteria become REQ-n; modules that exist become files_expected."""
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "reset.py").write_text("x = 1\n", encoding="utf-8")
    answers = "\n".join([
        "Users who forgot their password.",
        "The user.",
        "SMTP server.",
        "src/auth/reset.py, src/missing.py",
        "The user gets an email with a link; the link expires after 30 minutes",
    ]) + "\n"

    result = CliRunner().invoke(
        cli, ["plan", "Add password reset.", "--root", str(tmp_path), "--stdout"], input=answers
    )

    assert result.exit_code == 0, result.output
    text = result.stdout
    meta = yaml.safe_load(text.split("---\n", 2)[1])
    assert meta["requirements"] == ["REQ-1", "REQ-2"]
    assert meta["files_expected"] == ["src/auth/reset.py"]
    assert "- **REQ-1**: The user gets an email with a link" in text
    assert "- **REQ-2**: the link expires after 30 minutes" in text
    assert check_plan(text, slug="add-password-reset") == []


def test_check_command_reports_problems(tmp_path: Path) -> None:
    """`kingmadoc check` exits 1 and lists what is wrong."""
    _plan(tmp_path, VALID.replace("[REQ-1, REQ-2]", "[REQ-1]"))

    result = _run(tmp_path, "check", "password-reset")

    assert result.exit_code == 1
    assert "REQ-2" in result.output


def test_approve_flips_the_status_once(tmp_path: Path) -> None:
    """draft -> approved; approving again is an error that changes nothing."""
    path = _plan(tmp_path, VALID)

    first = _run(tmp_path, "approve", "password-reset")
    again = _run(tmp_path, "approve", "password-reset")

    assert first.exit_code == 0, first.output
    assert parse_plan(path.read_text(encoding="utf-8")).status == "approved"
    assert again.exit_code == 1 and "already approved" in again.output


def test_approve_refuses_a_broken_plan(tmp_path: Path) -> None:
    """A plan that fails `check` is not approved; the file stays as it was."""
    broken = VALID.replace("[REQ-1, REQ-2]", "[REQ-1]")
    path = _plan(tmp_path, broken)

    result = _run(tmp_path, "approve", "password-reset")

    assert result.exit_code == 1 and "REQ-2" in result.output
    assert path.read_text(encoding="utf-8") == broken


def test_a_slug_yaml_would_read_as_a_number_or_bool_stays_a_string(tmp_path: Path) -> None:
    """Descriptions like "No." or "2024." give slugs YAML reads as False or 2024."""
    for description, slug in (("No.", "no"), ("2024.", "2024"), ("Null.", "null")):
        result = CliRunner().invoke(
            cli, ["plan", description, "--root", str(tmp_path), "--no-input", "--stdout"]
        )

        assert result.exit_code == 0, result.output
        assert check_plan(result.stdout, slug=slug) == [], description
