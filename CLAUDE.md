# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

KingmaDoc is a Python CLI (Click, Jinja2, PyYAML) that generates feature docs for AI coding agents, to prevent "code blindness": `plan` writes a Feature Design Doc before implementation (C4/sequence/class diagrams in Mermaid, PlantUML or D2); `verify` writes a Feature Verification Doc afterwards. Currently phase 1: only C4 Context + Container are generated, `verify` is a work-in-progress stub that only writes a placeholder `<slug>-verify.md`, Claude Code only.

## Commands

```bash
uv venv -p 3.11 .venv && uv pip install -p .venv -e '.[dev]'   # setup
.venv/bin/pytest -q                                             # all tests
.venv/bin/pytest tests/test_config.py::test_unknown_key_raises  # single test
.venv/bin/kingmadoc plan "Add a feature." --no-input --stdout   # smoke test
python3 .claude/skills/checking-conventions/scripts/check_conventions.py  # convention check
```

A Stop hook (`.claude/settings.json`) runs the convention checker after every turn with uncommitted changes and feeds violations back. Fix them; for manual rules use the `checking-conventions` skill (repo dev tool, not the product skill).

Regenerate `examples/verify-mode-plan.md` after changing the template or generator (it's output of running `plan` on this repo with `-o examples/verify-mode-plan.md --force`; keep its answers).

## Architecture

Flow for `plan "<description>"` (`cli.py`): `config.load_config` → `plan.analyzer.analyze` → `plan.generator.build_questions` (prompts on stderr so `--stdout` stays clean; `--no-input`/closed stdin leaves them unanswered → "Open questions") → `plan.generator.build_plan_context` (pure; CLI passes `now`) → `render_plan` (every `PlanContext` field is a template variable) → `documents.write_documents` (all-or-nothing) to `<output_dir>/<slug>-plan.md`, plus one file per enabled `extra_designs.<name>` (`<slug>-functional-design.md`, `<slug>-technical-design.md`) via `render_extra_design`. To add an extra doc type: a field on `config.ExtraDesignsConfig`, an entry in `generator.EXTRA_DESIGNS`, a template, and a format block in `skill/SKILL.md` → prints one path per line.

- `config.py`: frozen dataclasses with defaults; `parse_config` rejects unknown keys and wrong types. `default_config_yaml()` produces the `init` output and must stay equal to the dataclass defaults (enforced by a test).
- `plan/analyzer.py`: pathlib walk with fnmatch excludes ("glob", hard cap `MAX_FILES_LIMIT` = 5000), manifest parsing (`pyproject.toml`, `requirements.txt`, `package.json`, `go.mod`, `Cargo.toml`, compose files → `DEPENDENCY_TECH`), regex import scanning ("grep"). Returns an immutable `CodebaseReport` (`kingmadoc plan --json` prints it via `report_to_dict`); `source_dirs` drives container inference (descends into `src/` layouts, skips tests/docs/examples).
- `skill/SKILL.md`: the product skill (Markdown-only KingmaDoc for users without Python; not the repo's `checking-conventions` dev skill). Its "Output format" must keep the same headings as `src/kingmadoc/templates/plan_default.md.j2` and `verify/stub.py` — `tests/test_skill.py` fails otherwise, so change both together. Must stay under 400 lines. `skill/cursor.md`, `codex.md`, `copilot.md` are generated from it by `scripts/build_skill_variants.py` — never edit them; rerun the script after changing SKILL.md (`tests/test_skill.py` fails on stale variants).
- `adr.py` (`kingmadoc adr "<title>"`, gated by `extra_designs.adr.enabled`): `adr_path` → `next_number` (max existing + 1, never reused) + `adr_filename` → `render_adr` (`templates/adr.md.j2`, bundled) → `docs/adr/<NNNN>-<slug>.md`. Not a mode; shares `naming.slugify` and `templating.load_template` with plan.
- `verify/stub.py` (`kingmadoc verify <slug>`): `find_plan` → `render_verify_stub` (pure, placeholder doc) → `write_document` to `<slug>-verify.md` next to the plan. Missing plan or malformed slug → `VerificationError` (exit 1). Modes may not import each other (E5, auto-checked), so shared I/O lives in `documents.py`.
- `diagrams/`: backend pattern, selected by `diagram_format` (`mermaid` default, `plantuml`, `d2`) via `diagrams.get_backend`. `base.py` has the `DiagramBackend` Protocol (`render_context/container/component/sequence/class`) and the shared pure model: `build_*` validate input, assign unique aliases and resolve relationships into frozen `Diagram`/`Node`/`Edge`. Backend modules (`mermaid.py`, `plantuml.py`, `d2.py`) only format that model and return a fenced block (templates must not add fences). Escaping differs per backend and is verified against the real tools: Mermaid `"`→`#quot;` (C4 titles drop `#`/`;`), PlantUML `"`→`<U+0022>`, D2 escapes `\`, `"`, `$`. Adding a backend: a module, an entry in `diagrams.BACKENDS` and `config.DIAGRAM_FORMATS`, snapshots via `KINGMADOC_UPDATE_SNAPSHOTS=1 pytest tests/test_diagram_backends.py`. Extra-doc templates pick their ER/flowchart placeholder by `diagram_format`. No knowledge of analysis: `generator.build_plan_context` maps analysis → C4 elements.
- Templates live in `src/kingmadoc/templates/` (shipped as package data). Security: `templating.load_template` loads bundled templates only from that package dir and never searches the analyzed project's root; a project template is used only when a `template:` setting gives an explicit path (`ConfigError` if missing or not a file). Every template renders in Jinja's `SandboxedEnvironment` (repos may be untrusted; see `tests/test_templating_security.py`). Jinja uses `StrictUndefined`, so every template variable must be passed.

## Conventions

All docs are indexed in `docs/index.md` (English only; add new `.md` files there). Rules: the **Rule summary** table at the top of `docs/conventions.md` (ID, status, auto/manual); open a rule's section only when needed. Key rules:

- Classes only for frozen dataclasses (data) and `typing.Protocol` extension points (behavior); everything else plain functions. Composition, not inheritance.
- Keep I/O in the shell (`cli.py`, file walking/writing); diagram builders, config parsing and detection stay pure.
- Type hints and docstrings on all public functions; `pathlib.Path` for all paths.
- No global state; config is passed explicitly, never imported as a module-level object.
- Raise subclasses of `kingmadoc.exceptions.KingmaDocError`; the CLI converts them to `click.ClickException`.
