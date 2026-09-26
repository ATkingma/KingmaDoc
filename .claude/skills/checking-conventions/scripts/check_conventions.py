#!/usr/bin/env python3
"""Check the automatable KingmaDoc conventions (see docs/conventions.md).

Usage:
    check_conventions.py            # report violations; exit 1 if any
    check_conventions.py --hook     # Claude Code Stop hook: exit 2 (feeds output to agent)

Output is one line per violation: ``path:line: RULE message``. Stdlib only.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

PACKAGE = "kingmadoc"
BUILTIN_EXCEPTIONS = frozenset(
    {"Exception", "ValueError", "TypeError", "KeyError", "RuntimeError", "OSError",
     "IOError", "FileNotFoundError", "IndexError", "AttributeError", "NotImplementedError"}
)
MUTABLE_TYPES = frozenset({"list", "dict", "set"})
IO_CALLS = frozenset({"open", "read_text", "write_text", "read_bytes", "write_bytes",
                      "mkdir", "unlink", "print", "iterdir", "rglob", "glob"})
# Distinct Dutch function words; 3+ in a doc's prose means it is probably not English.
DUTCH_WORDS = frozenset({"het", "een", "niet", "voor", "zijn", "wordt", "worden", "ook",
                         "maar", "deze", "naar", "wij", "jij", "welke", "omdat", "zoals"})
DUTCH_THRESHOLD = 3
# Test output beyond this many lines is truncated; the agent can rerun pytest itself.
MAX_TOOL_LINES = 15


def main() -> int:
    """Run all checks and report; return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hook", action="store_true", help="run as a Claude Code Stop hook")
    parser.add_argument("--root", type=Path, default=None, help="project root")
    args = parser.parse_args()

    root = (args.root or Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).parents[4]))
    root = root.resolve()

    if args.hook:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        # Already continued once because of this hook: don't loop.
        if payload.get("stop_hook_active"):
            return 0
        if not _has_changes(root):
            return 0

    violations = list(_python_checks(root)) + list(_doc_checks(root)) + list(_tool_checks(root))
    if not violations:
        if not args.hook:
            print("All automatic convention checks passed.")
        return 0

    out = sys.stderr if args.hook else sys.stdout
    print(f"Convention check: {len(violations)} violation(s) (rules: docs/conventions.md)", file=out)
    for line in violations:
        print(line, file=out)
    if args.hook:
        print("Fix these before finishing. For manual rules, use the checking-conventions skill.",
              file=out)
        return 2
    return 1


# ---------------------------------------------------------------- Python source


def _python_checks(root: Path) -> Iterator[str]:
    src = root / "src" / PACKAGE
    if not src.is_dir():
        return
    for path in sorted(src.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        module = ".".join(path.relative_to(root / "src").with_suffix("").parts)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            yield f"{rel}:{exc.lineno}: SYNTAX {exc.msg}"
            continue
        yield from _check_public_api(tree, rel)
        yield from _check_raises(tree, rel)
        yield from _check_pathlib(tree, rel)
        yield from _check_mutable_constants(tree, rel)
        yield from _check_frozen_dataclasses(tree, rel)
        yield from _check_imports(tree, rel, module)
        if module.startswith(f"{PACKAGE}.diagrams"):
            yield from _check_no_io(tree, rel)


def _check_public_api(tree: ast.Module, rel: str) -> Iterator[str]:
    """D3: public functions/methods need a docstring and full annotations."""
    def funcs(body: list[ast.stmt], in_class: bool) -> Iterator[tuple[ast.FunctionDef | ast.AsyncFunctionDef, bool]]:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield node, in_class
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                yield from funcs(node.body, True)

    for fn, is_method in funcs(tree.body, False):
        if fn.name.startswith("_"):
            continue
        if ast.get_docstring(fn) is None:
            yield f"{rel}:{fn.lineno}: D3 public function `{fn.name}` has no docstring"
        params = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
        if is_method and params and params[0].arg in {"self", "cls"}:
            params = params[1:]
        params += [a for a in (fn.args.vararg, fn.args.kwarg) if a is not None]
        missing = [a.arg for a in params if a.annotation is None]
        if missing:
            yield f"{rel}:{fn.lineno}: D3 `{fn.name}` missing type hints for: {', '.join(missing)}"
        if fn.returns is None:
            yield f"{rel}:{fn.lineno}: D3 `{fn.name}` missing return type"


def _check_raises(tree: ast.Module, rel: str) -> Iterator[str]:
    """D4: raise KingmaDocError subclasses, not builtin exceptions."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if isinstance(target, ast.Name) and target.id in BUILTIN_EXCEPTIONS:
                yield f"{rel}:{node.lineno}: D4 raises builtin `{target.id}`; use a KingmaDocError subclass"


def _check_pathlib(tree: ast.Module, rel: str) -> Iterator[str]:
    """D1: use pathlib, not os.path."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr == "path"
                and isinstance(node.value, ast.Name) and node.value.id == "os"):
            yield f"{rel}:{node.lineno}: D1 uses os.path; use pathlib.Path"
        elif isinstance(node, ast.Import) and any(
                a.name in {"os.path", "posixpath"} for a in node.names):
            yield f"{rel}:{node.lineno}: D1 imports os.path; use pathlib.Path"
        elif isinstance(node, ast.ImportFrom) and node.module in {"os.path", "posixpath"}:
            yield f"{rel}:{node.lineno}: D1 imports from os.path; use pathlib.Path"
        elif isinstance(node, ast.ImportFrom) and node.module == "os" and any(
                a.name == "path" for a in node.names):
            yield f"{rel}:{node.lineno}: D1 imports os.path; use pathlib.Path"


def _check_mutable_constants(tree: ast.Module, rel: str) -> Iterator[str]:
    """D6: module-level constants must be immutable."""
    mutable_nodes = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names, value = [node.target.id], node.value
        else:
            continue
        if not names or names[0] == "__all__" or value is None:
            continue
        is_mutable = isinstance(value, mutable_nodes) or (
            isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id in MUTABLE_TYPES)
        if is_mutable:
            yield (f"{rel}:{node.lineno}: D6 module constant `{names[0]}` is mutable; "
                   "use tuple/frozenset/MappingProxyType")


def _check_frozen_dataclasses(tree: ast.Module, rel: str) -> Iterator[str]:
    """E2: frozen dataclasses must not declare list/dict/set fields."""
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        if not any(_is_frozen_dataclass(d) for d in cls.decorator_list):
            continue
        for stmt in cls.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                used = {n.id for n in ast.walk(stmt.annotation) if isinstance(n, ast.Name)}
                bad = used & MUTABLE_TYPES
                if bad:
                    yield (f"{rel}:{stmt.lineno}: E2 frozen `{cls.name}.{stmt.target.id}` uses "
                           f"{'/'.join(sorted(bad))}; use tuple/Mapping")


def _is_frozen_dataclass(decorator: ast.expr) -> bool:
    return (isinstance(decorator, ast.Call)
            and getattr(decorator.func, "id", getattr(decorator.func, "attr", "")) == "dataclass"
            and any(k.arg == "frozen" and getattr(k.value, "value", False) is True
                    for k in decorator.keywords))


def _check_imports(tree: ast.Module, rel: str, module: str) -> Iterator[str]:
    """E1/E5: click only in the CLI; modes and diagrams stay independent."""
    mode = module.split(".")[1] if module.count(".") >= 1 else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            targets = [node.module]
        else:
            continue
        for target in targets:
            top = target.split(".")
            if top[0] == "click" and module != f"{PACKAGE}.cli":
                yield f"{rel}:{node.lineno}: E1 imports click outside cli.py"
            if top[0] != PACKAGE or len(top) < 2:
                continue
            dep = top[1]
            if dep == "cli" and module != f"{PACKAGE}.__main__":
                yield f"{rel}:{node.lineno}: E5 imports {PACKAGE}.cli; the CLI is the outer shell"
            elif mode in {"plan", "verify"} and dep in {"plan", "verify"} and dep != mode:
                yield f"{rel}:{node.lineno}: E5 mode `{mode}` imports mode `{dep}`"
            elif mode == "diagrams" and dep in {"plan", "verify"}:
                yield f"{rel}:{node.lineno}: E5 diagrams imports mode `{dep}`"


def _check_no_io(tree: ast.Module, rel: str) -> Iterator[str]:
    """E1: diagram builders are pure."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name in IO_CALLS:
                yield f"{rel}:{node.lineno}: E1 diagrams module performs I/O (`{name}`)"


# ---------------------------------------------------------------- documentation


def _doc_checks(root: Path) -> Iterator[str]:
    """B5: every Markdown file is indexed, and written in English."""
    index = root / "docs" / "index.md"
    md_files = [p for p in _repo_files(root) if p.suffix == ".md"
                and not p.as_posix().startswith("docs/features/")]
    if index.is_file():
        text = index.read_text(encoding="utf-8")
        linked = {
            (index.parent / target).resolve()
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text)
            if "://" not in target
        }
        for rel in md_files:
            if rel.as_posix() != "docs/index.md" and (root / rel).resolve() not in linked:
                yield f"{rel.as_posix()}:1: B5 not linked from docs/index.md"
    elif md_files:
        yield "docs/index.md:1: B5 documentation index is missing"

    for rel in md_files:
        prose = re.sub(r"```.*?```|`[^`]*`|\(http[^)]*\)", " ",
                       (root / rel).read_text(encoding="utf-8"), flags=re.S)
        found = DUTCH_WORDS & set(re.findall(r"[a-z]+", prose.lower()))
        if len(found) >= DUTCH_THRESHOLD:
            yield (f"{rel.as_posix()}:1: B5 looks non-English "
                   f"(found: {', '.join(sorted(found))}); docs must be English")


# ---------------------------------------------------------------- external tools


def _tool_checks(root: Path) -> Iterator[str]:
    """G1 tests; D1/D2 ruff and mypy when installed in the project venv."""
    venv_bin = root / ".venv" / "bin"
    python = venv_bin / "python" if (venv_bin / "python").exists() else Path(sys.executable)
    if (root / "tests").is_dir():
        yield from _run(root, "G1", [str(python), "-m", "pytest", "-q", "-x", "--no-header"],
                        required_module="pytest", python=python)
    if (venv_bin / "ruff").exists():
        yield from _run(root, "D1", [str(venv_bin / "ruff"), "check", "--quiet", "."])
    if (venv_bin / "mypy").exists():
        yield from _run(root, "D2", [str(venv_bin / "mypy"), "--strict", "src"])


def _run(root: Path, rule: str, cmd: list[str], required_module: str | None = None,
         python: Path | None = None) -> Iterator[str]:
    if required_module and python:
        probe = subprocess.run([str(python), "-c", f"import {required_module}"],
                               capture_output=True, cwd=root)
        if probe.returncode != 0:
            return
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
    if result.returncode == 0:
        return
    lines = (result.stdout + result.stderr).strip().splitlines()
    yield f"-:0: {rule} `{' '.join(Path(cmd[0]).name if i == 0 else c for i, c in enumerate(cmd))}` failed:"
    tail = lines[-MAX_TOOL_LINES:]
    if len(lines) > MAX_TOOL_LINES:
        yield f"    … {len(lines) - MAX_TOOL_LINES} lines omitted"
    yield from (f"    {line}" for line in tail)


# ---------------------------------------------------------------- git helpers


def _repo_files(root: Path) -> list[Path]:
    """Tracked + untracked, non-ignored files relative to root."""
    result = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"],
                            capture_output=True, text=True, cwd=root)
    if result.returncode != 0:
        return []
    return [Path(line) for line in result.stdout.splitlines() if (root / line).is_file()]


def _has_changes(root: Path) -> bool:
    """True if the working tree has uncommitted changes (or git is unavailable)."""
    result = subprocess.run(["git", "status", "--porcelain"],
                            capture_output=True, text=True, cwd=root)
    return result.returncode != 0 or bool(result.stdout.strip())


if __name__ == "__main__":
    sys.exit(main())
