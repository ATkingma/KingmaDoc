# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Design models (roadmap WP8): each extra design document contains design models
  (sections), selected per document with `extra_designs.<document>.models`
  (default: all models of that document).
- `extra_designs.domain_design`: domain model diagram and event storming.
- `extra_designs.security_design`: STRIDE threat model with the elements KingmaDoc
  detected, and a "who may do what" permissions matrix.
- `technical_design`: a module dependency graph derived from the imports between the
  project's own Python modules (merged into packages above 25 modules).
- `kingmadoc analyze` reports `module_dependencies` (also in `--json`).
- Agent skill `documenting-existing-features`: documents a feature that already exists, as
  built (status `implemented`), in the plan format plus an implementation map with file
  and line references.

## [0.1.1] - 2026-09-26

First public release, including all fixes from the pre-release review. Upgrading from
the unpublished 0.1.0: move `extra_designs.adr` to a
top-level `adr:` block, and use `kingmadoc analyze --json` instead of `plan --json`.

### Security

- Templates: `kingmadoc` no longer loads templates from the analyzed project's root,
  so running it in an untrusted repository cannot execute code from that repository.
  All templates render in Jinja's sandbox, and a project template is used only when
  `template:` names an explicit path (`ConfigError` if it is missing or not a file).
- Config: `output_dir` must resolve inside the project root (symlinks resolved first);
  a repository's config can no longer make `plan` write outside the project.
- Analyzer: import scanning no longer takes quadratic time on long runs of blank lines;
  a crafted file could stall `plan` for minutes (50k blank lines: 75 s → 0.04 s).

### Fixed

- CLI: `plan --stdout` no longer crashes with `UnicodeEncodeError` when stdout is not
  UTF-8 (piped output on Windows); stdout is written as UTF-8.
- CLI: `verify` no longer crashes with an unhandled `ValueError` when `output_dir` is an
  absolute path outside the project; it reports a config error instead.
- Documents: writing several documents is now truly all-or-nothing; a failure part-way
  restores replaced files and removes new ones.
- Analyzer: a manifest with a wrongly typed table or list (e.g. `dependencies = 5`) no
  longer crashes the analysis.
- Analyzer: manifests saved with a UTF-8 byte-order mark are parsed instead of skipped.
- Analyzer: Compose images with a registry port (`registry.local:5000/postgres:16`)
  are recognized by their image name.
- Summaries: the first sentence is no longer cut at `e.g.`, `i.e.`, `etc.`, `vs.`,
  `cf.` or `approx.`, and only ends before a capital letter.
- Slugs: accented letters are transliterated (`café` → `cafe`); descriptions without
  Latin letters get a short hash instead of all sharing the slug `feature`.
- Diagrams: test directories (`__tests__`, `spec`, `src/tests`, ...) are no longer
  inferred as C4 containers, and loose `src/*.py` files no longer add a `src` container
  next to `src/<pkg>`.
- Diagrams: elements with the same name no longer produce wrong arrows
  (`Rel(user, user)`); duplicate names are rejected, and generated names are unique.
- ADRs: date-named files such as `docs/adr/2024-q3-review.md` no longer set the next
  ADR number.

### Changed

- Config: `adr` is a top-level block, `adr: {enabled, template}`; `extra_designs.adr`
  is rejected as an unknown key.
- Config: each extra design (`extra_designs.<name>.template`) and `adr.template` can
  select its own template.
- CLI: `plan` always requires a description; its `--json` option moved to
  `kingmadoc analyze --json`.
- Diagrams: `render_context(relationships=None)` is replaced by the keyword
  `default_relationships: bool = True`; explicit relationships are drawn in addition to
  the default arrows.
- API: `write_document` takes `(path, content)`, like `write_documents`.
- Packaging: bundled templates live in `src/kingmadoc/templates/`; the sdist no longer
  contains the repository's Claude Code dev tooling (`.claude/`).
- Development: Ruff and `mypy --strict` are enforced in CI (new `lint` job), and
  GitHub Actions are pinned to commit SHAs.

### Added

- CLI: `kingmadoc analyze [--json]` prints the codebase analysis.
- Config: `analyzer.max_lines_per_file` (default 2000) limits how many lines per source
  file are read when detecting frameworks; manifests are always read in full.
- Analyzer: Cargo `[workspace.dependencies]` and `[target.*.dependencies]`, PEP 735
  `[dependency-groups]`, Poetry `[tool.poetry.group.*.dependencies]` and npm
  `optionalDependencies` are read.
- Generator: importing it fails if `EXTRA_DESIGNS` and the `extra_designs` config
  fields disagree, instead of failing during `plan`.
- Tests for `init`, custom templates, Ctrl-C during questions, atomic writes, the skill
  variant `--check`, Poetry dependencies and `verify --config`.

## [0.1.0] - 2026-09-26

Internal milestone; never published. Its contents first shipped in 0.1.1.

### Added

- `kingmadoc plan "<description>"`: analyzes the codebase, asks up to five clarifying
  questions and writes `docs/features/<slug>-plan.md` with a one-sentence summary,
  scope (in / out), assumptions, risks, C4 Context and C4 Container diagrams, open
  questions and a codebase appendix. Options: `--no-input`, `--stdout`, `--output`,
  `--force`, `--config`, `--root`.
- `kingmadoc plan --json`: the codebase analysis as JSON (file count, language
  breakdown, top-level directories, entry points, config files, test directories and
  detected stack). The analysis reads `pyproject.toml`, `requirements.txt`,
  `package.json`, `go.mod`, `Cargo.toml` and Docker Compose files, and stops at 5000 files.
- `kingmadoc verify <slug>`: work-in-progress stub that writes a placeholder
  `<slug>-verify.md` next to the plan (exit code 1 if the plan does not exist).
- `kingmadoc adr "<title>"`: numbered Architecture Decision Records in
  `docs/adr/<NNNN>-<slug>.md`, enabled with `extra_designs.adr.enabled`.
- `kingmadoc init`: writes `.featuredoc.yml` with every default and a comment per key.
- Optional extra documents next to the plan: `<slug>-functional-design.md` (user flows,
  edge cases, business rules, permissions) and `<slug>-technical-design.md` (database
  schema, API contracts, error handling, performance, security).
- Diagram backends: Mermaid (default), PlantUML (C4-PlantUML) and D2, selected with
  `diagram_format`, each with C4 Context/Container/Component, sequence and class diagrams.
- Markdown-only agent skill `skill/SKILL.md` for Claude Code, with generated variants
  for Cursor (`skill/cursor.md`), Codex (`skill/codex.md`) and GitHub Copilot
  (`skill/copilot.md`). The skill performs plan and full verify without Python.
- Documentation: README, CONTRIBUTING, conventions (`docs/conventions.md`) and an
  example plan doc (`examples/verify-mode-plan.md`).
- CI on Python 3.11–3.13 on Linux, macOS and Windows.

[Unreleased]: https://github.com/ATkingma/KingmaDoc/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/ATkingma/KingmaDoc/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ATkingma/KingmaDoc/releases/tag/v0.1.0
