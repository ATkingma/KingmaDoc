"""The project's build, test and lint commands: found in its files, run only on request.

Running commands from a repository executes its code, so ``kingmadoc verify`` runs them
only with ``--run-checks``; the repository's own config cannot switch that on.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

KINDS: tuple[str, ...] = ("Build", "Tests", "Lint")
_CONFIG_KEYS: Mapping[str, str] = MappingProxyType(
    {"Build": "build", "Tests": "test", "Lint": "lint"}
)
OUTPUT_LINES = 5
# Files detect_commands reads (the CLI passes their text); *.sln/*.csproj by suffix.
MARKER_FILES: tuple[str, ...] = (
    "Makefile", "package.json", "Cargo.toml", "go.mod", "pyproject.toml", "pytest.ini",
    "ruff.toml", "setup.cfg", "tox.ini",
)


@dataclass(frozen=True)
class CheckCommand:
    """A command that checks the project, and where KingmaDoc found it."""

    kind: str
    command: str
    source: str


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one command; ``passed`` is None when it was not run."""

    kind: str
    command: str
    passed: bool | None
    detail: str


def detect_commands(
    files: Mapping[str, str], configured: Mapping[str, str | None] | None = None
) -> tuple[CheckCommand, ...]:
    """Find the build, test and lint commands (at most one each, in :data:`KINDS` order).

    Configured commands win; then a Makefile target, npm scripts, Cargo, Go, .NET and
    Python tools, in that order.

    Args:
        files: Top-level project file name -> text (see :data:`MARKER_FILES`).
        configured: ``verify.build/test/lint`` from the config.

    Returns:
        The commands found.
    """
    found: dict[str, CheckCommand] = {}

    def offer(kind: str, command: str, source: str) -> None:
        found.setdefault(kind, CheckCommand(kind, command, source))

    for kind, key in _CONFIG_KEYS.items():
        if configured and configured.get(key):
            offer(kind, str(configured[key]), ".featuredoc.yml")
    make = files.get("Makefile", "")
    for kind, target in (("Build", "build"), ("Tests", "test"), ("Lint", "lint")):
        if re.search(rf"^{target}\s*:", make, re.M):
            offer(kind, f"make {target}", "Makefile")
    scripts = _npm_scripts(files.get("package.json"))
    for kind, script in (("Build", "build"), ("Tests", "test"), ("Lint", "lint")):
        if script in scripts:
            offer(kind, "npm test" if script == "test" else f"npm run {script}", "package.json")
    if "Cargo.toml" in files:
        cargo = ("cargo build", "cargo test", "cargo clippy")
        for kind, command in zip(KINDS, cargo, strict=True):
            offer(kind, command, "Cargo.toml")
    if "go.mod" in files:
        for kind, command in zip(KINDS, ("go build ./...", "go test ./...", "go vet ./..."),
                                 strict=True):
            offer(kind, command, "go.mod")
    dotnet = next((name for name in sorted(files) if name.endswith((".sln", ".csproj"))), None)
    if dotnet:
        offer("Build", "dotnet build", dotnet)
        offer("Tests", "dotnet test", dotnet)
    pyproject = files.get("pyproject.toml", "")
    if "[tool.pytest" in pyproject:
        offer("Tests", "pytest", "pyproject.toml")
    elif "pytest.ini" in files:
        offer("Tests", "pytest", "pytest.ini")
    if "ruff.toml" in files or "[tool.ruff" in pyproject:
        offer("Lint", "ruff check .", "ruff.toml" if "ruff.toml" in files else "pyproject.toml")
    return tuple(found[kind] for kind in KINDS if kind in found)


def run_check(root: Path, check: CheckCommand, timeout: int) -> CheckResult:
    """Run one command in ``root`` without a shell and keep the end of its output.

    Args:
        root: Project root (the working directory).
        check: The command.
        timeout: Seconds before it is stopped.

    Returns:
        Passed (exit code 0) or failed, with the last lines of output as the detail.
    """
    try:
        # Windows parses a command line itself (CreateProcess); elsewhere split it here.
        args: str | list[str] = check.command if os.name == "nt" else shlex.split(check.command)
        done = subprocess.run(  # noqa: S603 - opt-in (--run-checks), no shell
            args, cwd=root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False,
        )
    except FileNotFoundError:
        return CheckResult(check.kind, check.command, False, "command not found")
    except subprocess.TimeoutExpired:
        return CheckResult(check.kind, check.command, False, f"timed out after {timeout} s")
    except (OSError, ValueError) as exc:
        return CheckResult(check.kind, check.command, False, f"could not run: {exc}")
    lines = [line.strip() for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    tail = " / ".join(lines[-OUTPUT_LINES:])
    if done.returncode == 0:
        return CheckResult(check.kind, check.command, True, "passed")
    return CheckResult(check.kind, check.command, False,
                       f"failed (exit {done.returncode}): {tail}" if tail else "failed")


def _npm_scripts(text: str | None) -> Mapping[str, str]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts") if isinstance(data, dict) else None
    return scripts if isinstance(scripts, dict) else {}
