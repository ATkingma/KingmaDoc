# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-26

First public release.

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

[Unreleased]: https://github.com/ATkingma/KingmaDoc/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ATkingma/KingmaDoc/releases/tag/v0.1.0
