# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `explaining-code` 5.1 triggers on more requests: how something works, what a PR or
  commit changed, onboarding, walkthroughs, architecture or UML diagrams of existing
  code, and Dutch phrasings ("leg uit", "hoe werkt", "wat is er veranderd").
- `explaining-code` 5.0: real C4 diagrams in Simon Brown's notation (system context,
  container, component, code, landscape, dynamic, deployment; title, legend, element
  type, technology and description, labelled one-way arrows, one colour palette) and
  the other models the code calls for, picked from a decision table: UML sequence,
  state machine, class and domain model, package, activity with swimlanes, use case,
  ER (crow's foot), data flow with trust boundaries, event flow and DDD context map.
  Every model has notation rules and a checklist the agent goes through; tests check
  that every example follows its rules and compiles.
- `explain.documents`: `single` (default) or `split`, which writes a cover `README.md`,
  a `functional.md` and a `technical.md`; the user can also ask for it.
- One folder per explained subject: `docs/explain/<NNNN>-<name>/README.md` plus its
  `img/`, with a unique ID that is never reused. `kingmadoc explain new "<name>"` picks
  or reuses the folder and keeps the index `docs/explain/README.md` up to date (so does
  `kingmadoc render`); a README's images are named `img/figure-<n>.svg`.
  `explaining-code` 4.1 writes there.
- `kingmadoc skills install` updates skill files an earlier KingmaDoc installed without
  `--force`; only files edited locally need `--force`. A `.kingmadoc-skill.json`
  manifest per skill folder records what was installed; files a skill no longer ships
  are removed when unchanged.
- `kingmadoc --version` shows the installed git commit (`0.2.0.dev0 (git 29244f7)`)
  or `(editable)`, so an update is visible; the version is now `0.2.0.dev0`.
- Design models (roadmap WP8): each extra design document contains design models
  (sections), selected per document with `extra_designs.<document>.models`
  (default: all models of that document).
- `extra_designs.domain_design`: domain model diagram and event storming.
- `extra_designs.security_design`: STRIDE threat model with the elements KingmaDoc
  detected, and a "who may do what" permissions matrix.
- `technical_design`: a module dependency graph derived from the imports between the
  project's own Python modules (merged into packages above 25 modules).
- `kingmadoc analyze` reports `module_dependencies` (also in `--json`).
- Agent skill `explaining-code`: explains existing code with pictures, for a feature, a
  branch (what it changed), a whole project or a part of one. Writes `docs/explain/*.md`
  with the big picture, one sequence diagram per main action, the building blocks, the
  data and a where-to-find-what table; no audit or risk list, at most three questions.
- `kingmadoc render <doc>`: renders the D2 diagrams in a Markdown document to SVG images
  next to it and replaces each diagram with its image; the D2 source moves to
  `img/*.d2` next to the image, so the document shows only pictures. D2 is
  downloaded automatically on first use (pinned, SHA-256-verified; opt out with
  `KINGMADOC_D2_DOWNLOAD=0`), so nothing has to be installed besides KingmaDoc.
- `kingmadoc skills install [--agent claude|cursor|codex|copilot]`: installs the bundled
  agent skills into the project; with `--vscode` it also makes VS Code open
  `docs/explain/*.md` as a rendered preview (never without asking).
- `explaining-code` 4.0: writes an arc42 document by default (C4 levels 1-4, runtime
  and deployment views, decisions, glossary; quality and risks only as documented), or
  the compact C4 format with `explain.format: c4`. Every figure is numbered and
  decoded by a parts or arrows table instead of prose.
- `explain.format` in `.featuredoc.yml` (`arc42` default, or `c4`).

### Fixed

- `kingmadoc render` no longer fails with "Invalid cross-device link" (Errno 18) when
  the system temp dir is on another disk than the project.
- `explaining-code` never asks the user to install D2 (`kingmadoc render` downloads it)
  and tells an outdated install to update with `pipx reinstall kingmadoc` instead of
  `pipx install --force`, which fails on recent pipx versions.

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
