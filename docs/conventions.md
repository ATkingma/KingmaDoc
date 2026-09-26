# KingmaDoc conventions

Status: **adopted** = code follows it now; **planned** = agreed, not implemented.
Check: **auto** = enforced by `.claude/skills/checking-conventions/scripts/check_conventions.py`
(runs after every agent turn via a Stop hook); **manual** = reviewer judgment.
When you implement a planned rule, update its status here and in the details below.

## Rule summary

| ID | Rule | Status | Check |
|---|---|---|---|
| A1 | Ship a `SKILL.md` (Agent Skills standard; gerund `name`, third-person `description`) | adopted (partly) | manual |
| A2 | `SKILL.md` < 500 lines; details in `reference/*.md`, one level deep; TOC if > 100 lines | adopted (partly) | manual |
| A3 | Skill tells agents to *run* the CLI, not read the source | adopted (partly) | manual |
| A4 | ≥ 3 eval scenarios in `evals/` before extending the skill | planned | manual |
| B1 | Requirements as `REQ-n` in EARS notation; tasks/tests reference IDs | planned | manual |
| B2 | `<slug>-plan.md` starts with machine-readable YAML frontmatter | planned | manual |
| B3 | Feature docs are never deleted; `<slug>-verify.md` sits next to `<slug>-plan.md` | planned | manual |
| B4 | Diagrams are text in fenced blocks (Mermaid default; PlantUML, D2); inferred content is labelled | adopted | manual |
| B5 | Every Markdown file is linked from `docs/index.md`; all docs in English | adopted | auto (index) |
| C1 | No code changes before the design doc is approved (`yes` / `edit` / `stop`) | adopted (skill) | manual |
| C2 | `plan` asks at most 5 questions | adopted | manual |
| C3 | `verify` detects build/test/lint commands and stores them in config | planned | manual |
| D1 | PEP 8 via Ruff; `pathlib` instead of `os.path` | planned (pathlib: adopted) | auto (pathlib) |
| D2 | `mypy --strict` | planned | auto once installed |
| D3 | Public functions: full type hints + Google-style docstring | adopted | auto |
| D4 | Raise only `KingmaDocError` subclasses in `src/` | adopted | auto |
| D5 | `snake_case` / `PascalCase` / `UPPER_CASE` naming | adopted | manual |
| D6 | No global state; module constants immutable | adopted | auto (mutable constants) |
| E1 | Functional core, imperative shell: `click` only in `cli.py`; `diagrams/` does no I/O | adopted (partly) | auto |
| E2 | Frozen dataclasses hold no `list`/`dict`/`set` fields | adopted | auto |
| E3 | Extension points are `typing.Protocol`s | adopted (diagrams) | manual |
| E4 | Composition over inheritance | adopted | manual |
| E5 | Modes don't import each other; `diagrams/` imports no mode | adopted | auto |
| F1 | Profile before optimizing | adopted | manual |
| F2 | Benchmark hot paths with `pytest-benchmark` | planned | manual |
| F3 | Walk directories with `os.scandir`, not `Path.iterdir` + `is_*()` | planned | manual |
| F4 | Every limit/constant has a one-line reason | planned | manual |
| G1 | Test suite passes | adopted | auto |
| G2 | Branch coverage with a CI minimum | planned | manual |
| G3 | Property-based tests (Hypothesis) for parsers and transformers | planned | manual |
| G4 | Mutation testing (mutmut) once the codebase grows | planned | manual |
| G5 | Architecture contracts in `import-linter` | planned | manual |
| G6 | Decisions recorded as MADR ADRs in `docs/adr/` | planned | manual |
| G7 | Dependency security (`pip-audit`, Ruff `S`) and committed `uv.lock` | planned | manual |
| G8 | Conventional Commits, SemVer, `CHANGELOG.md` | planned | manual |

Details per rule follow. Read only the section you need.

## A. Skill conventions

### A1. Ship a `SKILL.md` following the Agent Skills open standard — adopted (partly)

[`skill/SKILL.md`](../skill/SKILL.md) exists. Deviation: `name` is `kingmadoc` (the
product name users type), not a gerund.

The CLI is the engine; agents discover it through a `SKILL.md` with YAML frontmatter.
The format is an open standard (agentskills.io) supported by Claude Code, Codex,
Cursor, Copilot, VS Code, and others, so this is also the path to multi-agent support.

- `name`: lowercase, digits, hyphens; max 64 chars; no "claude"/"anthropic".
  Prefer a gerund form, e.g. `documenting-features`.
- `description`: max 1024 chars, **third person**, states _what_ it does and _when_ to
  use it, e.g. "Generates a Feature Design Doc before implementation and a Feature
  Verification Doc afterwards. Use when planning a new feature, or when checking what
  an agent built against its design."

### A2. Progressive disclosure — adopted (partly)

`SKILL.md` is one self-contained file under 400 lines with a table of contents, so it
can be copied into a project on its own. Split into `reference/` once it nears 500.

- `SKILL.md` body under 500 lines: workflow and commands only.
- Details in `reference/plan.md`, `reference/verify.md`, linked directly from
  `SKILL.md` (references one level deep, never chained).
- Reference files over 100 lines start with a table of contents.

### A3. Execute, don't read — adopted (partly)

The skill runs `kingmadoc plan --json` for the analysis when the CLI is installed and
falls back to Glob/Grep otherwise (the no-install use case).

`SKILL.md` tells the agent to _run_ `kingmadoc plan …` / `kingmadoc verify …`, not to
read the source. Deterministic work (analysis, diagram generation, validation) belongs
in the CLI, not in agent-generated code.

### A4. Evaluations before expansion — planned

Keep at least three eval scenarios (query, fixture repo, expected behavior) in
`evals/`. Run them with and without the skill; only add instructions that fix an
observed failure.

## B. Document conventions

### B1. Numbered requirements in EARS notation — planned

Requirements in the design doc use IDs and EARS syntax:

```markdown
- **REQ-1**: WHEN a user requests a password reset THE SYSTEM SHALL email a single-use link.
- **REQ-2**: IF the link is older than 30 minutes THEN THE SYSTEM SHALL reject it.
```

Tasks and tests reference these IDs. This is what makes `verify` possible: each REQ-ID
can be checked against code and tests.

### B2. Machine-readable frontmatter in the plan doc — planned

```yaml
---
kingmadoc: 1 # document format version
feature: password-reset
status: draft # draft | approved | implemented | partial
requirements: [REQ-1, REQ-2]
files_expected: [src/app/auth/reset.py]
---
```

`verify` parses this block instead of scraping Markdown. A `kingmadoc check <doc>`
command validates it (plan → validate → execute pattern).

### B3. Docs are a permanent decision log — planned

Plan docs are never deleted. `verify` writes `<slug>-verify.md` next to `<slug>-plan.md`
in `docs/features/`, so any later session can pick up where the last one ended.

### B4. Diagrams are text, inferred content is marked — adopted

All diagrams are text in fenced code blocks: Mermaid by default, or PlantUML / D2 via
`diagram_format`. No images, no rendering step inside KingmaDoc. The agent skill always
uses Mermaid. Anything inferred from the codebase
(containers, modules) is labelled as such, so readers know to review it.

### B5. One documentation index, English only — adopted

Every Markdown file (except generated `docs/features/` output) is linked from
`docs/index.md`. All documentation is written in English.

## C. Workflow conventions

### C1. Approval gate before code — adopted (skill)

The skill asks for `yes` / `edit` / `stop` after writing the plan. The CLI only writes
the doc; the gate is the agent's job.

No source files change until the design doc is approved. After generation the agent
accepts only `yes`, `edit <changes>`, or `stop`. Status moves
`draft → approved → implemented | partial`.

### C2. At most five clarifying questions — adopted

`plan` asks up to `max_questions` (0–5) questions, covering problem, trigger,
integrations, affected modules, and acceptance criteria.

### C3. Detect and remember project commands — planned

`verify` auto-detects build/test/lint commands (pytest, npm, cargo, make) and writes
them back to `.featuredoc.yml`, so detection is not repeated every run.

## D. Python coding standards

### D1. Style: PEP 8 via Ruff — planned

Ruff replaces Black, isort, flake8, and pyupgrade. Line length 100. Suggested rules:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF", "D", "ANN", "PTH"]
ignore = ["D105", "D107"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D", "ANN"]
```

`PTH` enforces the "pathlib everywhere" rule; `ANN` and `D` enforce type hints and
docstrings.

### D2. Types: `mypy --strict` — planned

The rule "type hints everywhere" is only real when checked. Without `--strict`, mypy
silently skips unannotated functions.

### D3. Docstrings: Google style — adopted

`Args:`, `Returns:`, `Raises:` sections on all public functions. Private helpers
(`_name`) need a docstring only when the behavior is not obvious.

### D4. Errors: one exception hierarchy — adopted

All errors subclass `kingmadoc.exceptions.KingmaDocError`, one subclass per failure
domain (`ConfigError`, `AnalysisError`, `GenerationError`). Only `cli.py` converts
them to user-facing messages. Tests cover the error paths.

### D5. Naming — adopted

`snake_case` functions and variables, `PascalCase` classes, `UPPER_CASE` module
constants, leading underscore for module-private helpers.

### D6. No global state; explicit configuration — adopted

Config is loaded once in the CLI and passed down as an argument. Module-level
constants are allowed only when immutable (tuples, frozensets, `MappingProxyType`).

## E. Architecture and object-oriented design

KingmaDoc does not aim for "more OO" as a goal in itself. The rule is: **use classes
where they buy something — immutable data, and swappable behavior behind a
Protocol. Keep the rest as plain functions.** Deep inheritance trees are avoided.

### E1. Functional core, imperative shell — adopted (partly)

- **Shell** (side effects): `cli.py`, filesystem walking, file writes, prompts.
- **Core** (pure, no I/O): config parsing, tech detection from a file list, Mermaid
  builders, template context building.

`diagrams/` and `config.parse_config` are already pure. Next step: split
`analyzer.analyze` into an I/O part (walk + read) and a pure part (detect from paths
and contents), so detection is testable without a temp directory.

### E2. Immutable data as frozen dataclasses — adopted

Data passed between layers (`FeatureDocConfig`, `CodebaseReport`,
`PlanContext`) is `@dataclass(frozen=True)`. Use `tuple` instead of `list`, and
`Mapping` (backed by `MappingProxyType`) instead of `dict`, so they are deeply immutable.

### E3. Protocols for extension points — adopted (diagrams)

`diagrams.base.DiagramBackend` is the first one: each backend is a plain module
(`mermaid`, `plantuml`, `d2`) that satisfies the protocol, selected by
`diagrams.get_backend`. No backend classes or inheritance.

Phase 2 adds component, sequence, and class diagrams, and later other agents and
output formats. Define each extension point as a `typing.Protocol`, not an ABC:
implementations don't need to inherit anything, and tests can pass a simple fake.

```python
class DiagramBuilder(Protocol):
    """Builds one Mermaid diagram from the planning context."""

    name: str  # config key, e.g. "c4_context"

    def build(self, context: PlanContext) -> str: ...


class TechDetector(Protocol):
    """Detects technologies from the analyzed file set."""

    def detect(self, files: Sequence[Path], read: Callable[[Path], str]) -> set[str]: ...
```

The generator receives a `Mapping[str, DiagramBuilder]` as an argument, built in the
CLI. Adding a diagram then means adding one class and one registry entry, not editing
`render_plan`.

### E4. Composition over inheritance — adopted

Behavior is combined by passing objects in (dependency injection through constructor
or function arguments), not by subclassing. Use an ABC only when several
implementations must share real code; otherwise, use a Protocol.

### E5. One mode = one package — adopted

`plan/` and (phase 2) `verify/` each own their analyzer/generator. Shared building
blocks live in their own packages (`diagrams/`, and later e.g. `docs/` for
frontmatter parsing), never in one mode importing the other.

## F. Efficiency

Rule: measure first, then optimize only what a measurement points to.

### F1. Profile before optimizing — adopted

Use `python -m cProfile -s cumtime -m kingmadoc.cli plan X --no-input --stdout` or
`py-spy record -- kingmadoc plan X --no-input --stdout`. No speculative optimizations.

### F2. Benchmark hot paths — planned

Add `pytest-benchmark` tests for `analyze()` on a generated fixture tree (e.g. 10,000
files), so a slowdown fails like a regression instead of going unnoticed.

### F3. `os.scandir` for directory walks — planned

`Path.iterdir()` plus `is_symlink()`/`is_dir()`/`is_file()` costs up to three `stat`
syscalls per entry. `os.scandir()` returns cached file types (PEP 471: 2–20x faster
walks, much more on network filesystems). Rewrite `analyzer._iter_files` with
`os.scandir`, converting to `Path` only for yielded files. This is the one allowed
exception to "pathlib everywhere".

### F4. Justified limits — planned

Every limit gets a one-line reason (Anthropic calls unexplained values "voodoo
constants"), e.g. `MAX_GREP_BYTES = 512 * 1024  # larger files are generated or vendored`.

## G. Verifiability

Rule: correctness and decisions must be demonstrable, not assumed.

### G1. Test suite passes — adopted

`pytest` passes before a change is done. Tests cover error paths of every exception.

### G2. Branch coverage — planned

`pytest --cov=kingmadoc --cov-branch --cov-fail-under=85`. Line coverage alone is a
floor, not proof that tests check anything.

### G3. Property-based tests — planned

Use Hypothesis for functions that parse, validate, or transform input: `parse_config`,
`slugify`, `make_alias`, Mermaid escaping, `render_tree`. Properties state invariants
(e.g. "`make_alias` always returns a valid identifier") and Hypothesis searches for
counterexamples.

### G4. Mutation testing — planned

Once the codebase grows, run `mutmut` periodically to measure whether tests notice
broken code. Not on every commit (slow).

### G5. Architecture contracts — planned

Encode E1/E5 in `import-linter` so CI fails on a layering violation:

```toml
[tool.importlinter]
root_package = "kingmadoc"

[[tool.importlinter.contracts]]
name = "Layers"
type = "layers"
layers = ["kingmadoc.cli", "kingmadoc.plan | kingmadoc.verify", "kingmadoc.diagrams", "kingmadoc.config", "kingmadoc.exceptions"]
```

Until then, the convention checker (auto) covers the core of these rules.

### G6. Architecture Decision Records — planned

Significant decisions go in `docs/adr/NNNN-title.md` using the MADR minimal template
(context, decision, consequences). Candidates: Protocols over ABCs; templates at repo
root; strict unknown-key rejection in config.

### G7. Dependency security and reproducibility — planned

Enable Ruff `S` (bandit) rules, run `pip-audit` in CI, and commit `uv.lock` so every
install resolves the same versions.

### G8. Release discipline — planned

Conventional Commits (`feat:`, `fix:`), SemVer versions, and a `CHANGELOG.md` in Keep a
Changelog format.

## Sources

- [Skill authoring best practices — Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Agent Skills overview — Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Agent Skills open standard — Codex Knowledge Base](https://codex.danielvaughan.com/2026/05/05/agent-skills-open-standard-portable-skills-codex-cli-cross-agent/)
- [revagomes/spec-skill](https://github.com/revagomes/spec-skill)
- [Kiro feature specs (EARS)](https://kiro.dev/docs/specs/feature-specs/)
- [github/spec-kit](https://github.com/github/spec-kit)
- [Pimzino/claude-code-spec-workflow](https://github.com/Pimzino/claude-code-spec-workflow)
- [The Python code quality stack in 2026: Ruff + mypy](https://blog.marcosalonso.dev/the-complete-python-code-quality-stack-in-2026-ruff-mypy)
- [mypy: Protocols and structural subtyping](https://mypy.readthedocs.io/en/stable/protocols.html)
- [Modern Python OOP: ABC vs Protocol vs Dataclass](https://tiendu.github.io/2026/02/27/modern-python-oop-eng.html)
- [Functional Core, Imperative Shell](https://functional-architecture.org/functional_core_imperative_shell/)
- [PEP 471 – os.scandir()](https://peps.python.org/pep-0471/)
- [An Empirical Evaluation of Property-Based Testing in Python (ACM)](https://dl.acm.org/doi/10.1145/3764068)
- [mutmut documentation](https://mutmut.readthedocs.io/)
- [Import Linter – Layers contract](https://import-linter.readthedocs.io/en/v2.11/contract_types/layers/)
- [MADR – Markdown Architectural Decision Records](https://adr.github.io/madr/)
