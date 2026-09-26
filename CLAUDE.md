# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

KingmaDoc is a Python CLI (Click, Jinja2, PyYAML) that generates feature docs for AI coding agents, to prevent "code blindness": `plan` writes a Feature Design Doc before implementation (Mermaid C4/sequence/class diagrams); `verify` writes a Feature Verification Doc afterwards. Currently phase 1: only C4 Context + Container are generated, `verify` is a stub that exits 1, Claude Code only, Mermaid only.

## Commands

```bash
uv venv -p 3.11 .venv && uv pip install -p .venv -e '.[dev]'   # setup
.venv/bin/pytest -q                                             # all tests
.venv/bin/pytest tests/test_config.py::test_unknown_key_raises  # single test
.venv/bin/kingmadoc plan "Feature" -d "desc" --no-input --stdout   # smoke test
```

Regenerate `examples/verify-mode-design.md` after changing the template or generator (it's output of running `plan` on this repo).

## Architecture

Flow for `plan` (`cli.py`): `config.load_config` → `plan.analyzer.analyze` → `plan.generator.build_questions` (interactive prompts, written to stderr so `--stdout` stays clean) → `plan.generator.render_plan` → `write_document`.

- `config.py`: frozen dataclasses with defaults; `parse_config` rejects unknown keys and wrong types. `default_config_yaml()` produces the `init` output and must stay equal to the dataclass defaults (enforced by a test).
- `plan/analyzer.py`: pathlib walk with fnmatch excludes ("glob"), marker-file detection, regex import scanning ("grep"). Returns an immutable `AnalysisResult`; `source_dirs` drives container inference (descends into `src/` layouts, skips tests/docs/examples).
- `diagrams/c4.py`: pure string builders for Mermaid `C4Context`/`C4Container`; no knowledge of analysis. `generator.render_plan` maps analysis → C4 elements.
- Templates live in repo-root `templates/`, but ship in the wheel as `kingmadoc/templates` via hatch `force-include`. `generator.template_dirs` searches: project root → installed package → source checkout. Jinja uses `StrictUndefined`, so every template variable must be passed.

## Conventions

- Type hints and docstrings on all public functions; `pathlib.Path` for all paths.
- No global state; config is passed explicitly, never imported as a module-level object.
- Raise subclasses of `kingmadoc.exceptions.KingmaDocError`; the CLI converts them to `click.ClickException`.
