# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `explaining-code` skill 6.1, from a real arc42 session that needed six corrections:
  plain language at mbo level in the user's language (no coined words), a table when it
  is clearer than a figure, C4 blocks with name and `[type: technology]` only and a fixed
  width (the description goes into the table), no grids inside C4 boundaries, one arrow
  to an outer deployment node, a state diagram or plain flowchart instead of swimlanes
  with loops, and `pip install --pre kingmadoc` (plus a Windows fallback when the exe
  shim is blocked). arc42 starts with document control (versions, distribution,
  sources), gets a new section 2 "Starting situation" (the existing process, what the
  tool could already do by general pattern, the test cases with passes/fails) that
  `explain scaffold` writes too, and "Architecture constraints" with Constraint |
  Background per theme; later sections move up one number. A draw.io palette
  (`explain.palette: drawio`, light mode) with traffic-light status colours; UML classes
  as `|md` rectangles instead of `shape: class`; sequence colours; Balsamiq-style sketch
  wireframes with safe grid rules and a check that every text comes from the view.
- `kingmadoc render` warns about arrow labels of more than four words
  (`MAX_LABEL_WORDS`; a `[protocol]` counts as one) or with a line break, and about
  `shape: class` with its own fill.
- The same actors on every C4 level: the context's people and external systems appear
  in the container, component and deployment figures with the same keys, names, classes
  and order, and no invented or renamed actors (a role without code goes into the
  stakeholders table). `kingmadoc render` and `explain check` warn about a missing,
  extra, renamed or reordered actor (`explain.c4_actor_warnings`), `explain scaffold`
  starts each lower C4 block from the context's actors, and the C4 examples show them
  on every level. The skill never picks the compact c4 format on its own.
- `kingmadoc explain check` warns when a `[Screen]` wireframe has a text that the view
  named in its caption does not contain (best effort).

### Changed

- `kingmadoc render` embeds each image as a base64 data URI by default, so a document
  shows its pictures on its own; `--link` links `img/<name>.png` as before. The `img/`
  files and the `<!-- kingmadoc:diagram … -->` comment stay, so rendering again replaces
  the image instead of adding one, and documents with relative links are converted.
  `--light` also drops the white-fill warning (draw.io colours on white are fine there).

### Fixed

- `kingmadoc explain check` counts embedded (data-URI) images as present and reports
  how many pictures the explainer shows (it said "missing images: data:…" and "0
  pictures"); the evals' `pictures_only` check accepts them too.
- Explainers can no longer end up without pictures. `kingmadoc render` links the SVG of
  a diagram whose PNG conversion fails (a missing `resvg-py` wheel, a Rust panic in
  resvg) instead of failing the whole document, and `resvg-py` is loaded only when a
  PNG is made, so a platform without its wheel keeps every other command. The
  `explaining-code` skill (6.0) delivers first and asks afterwards: it never stops on a
  question before the document is written and rendered (screenshots are offered at
  hand-over, wireframes come first), and it must pass the new
  `kingmadoc explain check <folder>` (no placeholders, no unrendered D2, no missing
  images, no figure without a picture) before it hands over. The eval scenarios run
  the same check.

### Changed

- `kingmadoc render` links a PNG for each diagram, so the pictures show in every
  Markdown preview (VS Code, Visual Studio, Rider, GitHub, GitLab, Bitbucket; several
  block or mishandle SVG). The PNG is made offline with resvg (`resvg-py`, a small
  wheel for every platform) using D2's own embedded fonts; the SVG (dark mode) and the
  `.d2` source stay next to it, and `--format svg` links the SVG as before.
  `explaining-code` 5.8 no longer lets the agent convert images itself.
- `kingmadoc skills install --vscode-user`: VS Code opens explainers as a preview in
  every folder (user settings); the question in a terminal sets that up.
- Tidier diagrams: `kingmadoc render` lays figures out with ELK (straight,
  right-angled arrows with fewer crossings; a diagram that sets its own
  `layout-engine` keeps it) and warns about more than 12 arrows or two arrows between
  the same shapes. `explaining-code` 5.7: one flow direction, one arrow per pair, at
  most 12 arrows, labels of at most six words; C4 boundary labels sit top-left in a
  small font so arrows do not cross them. At hand-over the agent asks whether VS Code
  should open explainers as a preview (the pictures only show there) and sets it up on
  yes.
- Beta channel: every commit on `main` that passes CI is published to PyPI as a
  development version (`0.3.0.devN`); follow it with
  `pipx install --pip-args=--pre kingmadoc` and `pipx upgrade kingmadoc`.
- Fewer tokens for agents: `kingmadoc render` prints one line per document
  (`--verbose` lists every image), `kingmadoc explain facts --only routes,data` prints
  only the sections asked for, and `explaining-code` 5.6 works quietly, loads reference
  sections on demand (each long reference starts with its contents), lets a subagent
  read a big codebase and return a compact summary, fixes a figure by editing its
  `.d2`, and hands over in at most five lines. The `kingmadoc` skill does not paste the
  plan into the chat either.
- `kingmadoc skills install` asks in a terminal whether VS Code should open explainers
  as a rendered preview (default yes); `--vscode` / `--no-vscode` answer up front, and
  agents or pipes only get a tip. `kingmadoc render` says how to see the pictures
  (Ctrl+Shift+V) while that setting is missing.

### Added

- The functional design follows one red thread: user stories (one per `REQ-n`), a use
  case diagram, and per story `US-n` a use case `UC-n`, a screen design `S-n` (a
  screenshot when the screen exists, else a text wireframe) and evil user stories
  `EUS-n.m`, each pointing at a security measure `SM-n`. The technical design gets the
  threat model with those measures. Skill 1.2.0 writes the same.
- Threat models follow the Microsoft Threat Modeling Tool (template SDL TM Knowledge
  Base): its stencils (External Interactor, Process, Data Store, trust boundaries such
  as Internet Boundary), and its report: per interaction the tool's STRIDE threats, each
  with a state (Not Started, Not Applicable, Needs Investigation, Mitigation
  Implemented), a priority and a justification, plus the state summary. `threat_model`
  is now also a model of `technical_design` (default: on). The threats come from
  Microsoft's own knowledge base (the tool's default template, *SDL TM Knowledge Base
  (Core)* 4.1.0.11, MIT, bundled from microsoft/threat-modeling-templates):
  `kingmadoc threats <file>.yml` evaluates its generation rules for every data flow as
  the tool does and prints the data flow diagram (D2, Mermaid or PlantUML) and the
  report; `--types` lists the stencils. `explaining-code` uses it, or its generated
  `reference/threats.md` without the CLI.
- Every model is on by default and can be chosen: the functional design's parts are
  models now (`user_stories`, `use_case_diagram`, `use_cases`, `screen_designs`,
  `evil_user_stories`, `user_flows`, `edge_cases`, `business_rules`, `permissions`);
  `kingmadoc plan --models a,b` keeps only those (and switches on the documents that
  have them); `explain.models` lists what the explaining-code agent may draw, and the
  request can narrow it ("without screens").
- The functional design (FO) is for stakeholders: what the feature does and for whom,
  in plain words. Business rules, permissions and edge cases moved to the technical
  design (TO), which is for developers only: they are models of `technical_design` now
  (with where each is enforced and its test). The explainer's `functional.md` and
  `technical.md` split the same way; the threat model has its own reference,
  `reference/threat-model.md`.
- `kingmadoc explain scaffold "<subject>"` writes the empty explainer (arc42 or c4;
  one document, FO + TO, only an FO or only a TO; the chosen models) straight from the
  skill's reference formats, with the key facts, headings, tables and figure numbers
  filled in, so the agent no longer reads the output formats. `kingmadoc screenshots
  <url> /route=name …` captures screens of a running app (one browser with the optional
  `kingmadoc[screenshots]` extra, else `npx playwright`). The skill is shorter
  (SKILL.md about 3,400 instead of 4,900 tokens); user stories, screens and evil user
  stories have their own reference, `reference/stories.md`.
- `kingmadoc plan --documents split|functional|technical`: by default only the plan is
  written; "make an FO and TO" (or "functional and technical design", "split") adds
  both designs, "only an FO" / "only a TO" just that one. The plan skill (1.2.0) maps
  the request the same way.
- Explainers pick their documents from the request, without asking back: arc42 by
  default, "as an FO/TO" writes both, "only an FO" or "only a TO" writes just that one
  (`explain.documents: functional` / `technical` sets it per project).
- The arc42 explainer reads like a software architecture document: section 1 lists
  documented stakeholders and links the requirements (`REQ-n` plan docs); section 3
  splits into a Business context for stakeholders (actors, use case diagram, user
  stories with use case, screen and evil user stories) and a Technical context for
  developers; section 8 adds testability and the repository's stated conventions
  (code, branches, commits); section 10 lists the quality scenarios the tests cover
  (context, goal, how it is tested).
- `explaining-code` 5.9: "document an FO/TO" (functioneel/technisch ontwerp) writes the
  split explainer with the same red thread: user stories, per story a use case, a
  screenshot of the running app (the agent asks first; a D2 wireframe from the view code
  when it cannot run) and evil user stories; `technical.md` gets a threat model in
  Threat Modeling Tool style (data flow diagram in its notation, its threats per
  interaction, the security measures the code takes, sensitive data), which a single arc42 or c4 explainer also gets when the code has logins,
  tokens, personal data or uploads. "Document an arc42" picks the arc42 format.
- `kingmadoc explain facts` lists private modules from the dominator tree of the module
  graph (Python and JavaScript/TypeScript): what only one module leads to belongs to
  it, which shows the real component boundaries. A single entry point is left out.
- `explaining-code` model "Algorithm": a flowchart, at most 15 lines of pseudocode, the
  formula as `$$ … $$` (GitHub and VS Code render it), the invariant, the complexity and
  a trace table on a small input.

### Fixed

- Dark mode: the C4 style of `explaining-code` (5.5) set black title text and white
  boundaries and nodes, which were unreadable or glaring in dark mode. Titles and
  labels now follow the theme and boundaries are transparent; `kingmadoc render` warns
  about such styles in existing diagrams (fixed text colour without a fill, white
  fills, a `sequence_diagram` whose container key shows as a heading).
- `kingmadoc render`: images get normal file permissions (0644) instead of D2's private
  0600.

## [0.2.0] - 2026-09-27

Explain existing code with pictures, machine-readable plans, and a `verify` that
compares the code with its plan. Upgrading from 0.1.1:

- Update with `pipx reinstall kingmadoc` (or, once on PyPI, `pipx upgrade kingmadoc`),
  then run `kingmadoc skills install` again; it updates the skills without `--force`.
- Plans now start with YAML frontmatter and have a "Requirements" section. Plans from
  0.1.x have neither: `kingmadoc check` says so, and `verify` reports them as
  "Not verified". Regenerate the plan, or add the frontmatter by hand
  (`skill/reference/formats.md`).
- `kingmadoc verify` now compares the code with the plan and changes the plan's status
  (`implemented` / `partial`); it runs project commands only with `--run-checks`.
- `.vscode/settings.json` is only written with `skills install --vscode`.
- Python API: `skills.install_skills` returns an `InstallResult`; `verify.stub` is
  replaced by `verify.locate` (`find_plan`) and `verify.report` (`render_verify`).

### Added

**Explain existing code** (agent skill `explaining-code` 5.4, roadmap WP12)

- Explains a feature, a branch (what it changed), a project or a part of one with
  pictures: an arc42 document by default, or the compact C4 format
  (`explain.format: c4`); one document, or functional and technical apart
  (`explain.documents: split`). No audit or risk list; at most three questions.
- Real C4 diagrams in Simon Brown's notation, plus the models the code calls for, picked
  from a decision table: UML sequence, state machine, class and domain model, package,
  activity with swimlanes, use case, ER, data flow with trust boundaries, event flow and
  DDD context map. Tests check that every example follows its notation and compiles.
- One folder per subject, `docs/explain/<NNNN>-<name>/`, with an ID that is never
  reused: `kingmadoc explain new "<name>"` picks or reuses it and keeps the index
  `docs/explain/README.md` up to date.
- `kingmadoc explain facts [--base REF] [--json]`: what can be read from the code
  without guessing, for the agent to draw from: the stack, project references (.NET),
  Python and JavaScript/TypeScript module dependencies, routes with their access rules
  (ASP.NET, Next.js, Django, FastAPI, Flask, Express), .NET services, the data model
  (EF Core, Prisma, Django, SQLAlchemy, TypeORM) and, with `--base`, a branch's commits
  and changed files.
- `kingmadoc explain status [--check]`: which explainers the code changed under since
  the commit they are based on.

**Pictures**

- `kingmadoc render <doc>`: turns the D2 diagrams in a Markdown document into SVG images
  next to it; the document shows only the pictures, the sources go to `img/*.d2`. The
  images follow the viewer's dark mode (`--light` for light only). D2 is downloaded on
  first use (pinned, SHA-256-verified; `KINGMADOC_D2_DOWNLOAD=0` to opt out).

**Plans and verification** (roadmap WP1, WP2)

- Plans start with YAML frontmatter (`kingmadoc: 1`, `feature`, `status`,
  `requirements`, `files_expected`) and have a "Requirements" section with `REQ-n` IDs
  from the acceptance criteria. `kingmadoc check <slug>` validates a plan;
  `kingmadoc approve <slug>` sets `status: approved`, the gate before code.
- `kingmadoc verify <slug>` compares the code with its plan: the files changed since
  the plan (git, including uncommitted work), expected files never touched, changes
  outside the plan, `REQ-n` no test or commit mentions, containers added or gone, and
  code written before approval. Build, test and lint (from `verify:` in the config, or
  detected) run only with `--run-checks`. The plan's status becomes `implemented` or
  `partial`.
- Design documents: design models per document (`extra_designs.<document>.models`),
  `domain_design` (domain model, event storming) and `security_design` (STRIDE threat
  model, permissions matrix); `technical_design` gets a module dependency graph, and
  `kingmadoc analyze` reports `module_dependencies`.

**Installing and updating**

- `kingmadoc skills install [--agent claude|cursor|codex|copilot]` installs both
  skills into the project and updates them later without `--force` (only local edits
  need it); `--vscode` makes VS Code open explainers as a rendered preview.
- `kingmadoc --version` shows the installed git commit (`0.2.0 (git 1a2b3c4)`).

**Development**

- Skill evaluations (roadmap WP5): scenarios in `evals/`, run with
  `python scripts/run_evals.py --compare --record`.

### Changed

- The version comes from the git tag (`hatch-vcs`): every commit after a release has a
  higher development version, so updates of a git install are visible.
- Release workflow: a `v*` tag builds, tests and publishes to PyPI (trusted
  publishing) and creates the GitHub release (`docs/releasing.md`).
- The `kingmadoc` skill (1.1) is split into `SKILL.md` and `reference/`
  (formats, diagram rules); the Cursor, Codex and Copilot files still hold everything.
- Quality: branch coverage with a 90 % minimum, property-based tests (Hypothesis),
  `import-linter` contracts for the architecture rules, `uv.lock`, `pip-audit` and
  Ruff's security rules in CI.
- API: `skills.install_skills` returns an `InstallResult`; `verify.stub` is replaced by
  `verify.locate` and `verify.report`.

### Fixed

- Analyzer: imports in test directories no longer add frameworks to the detected stack.
- Analyzer: build output of Next.js (`.next/`), Nuxt and SvelteKit is no longer
  analyzed as source.

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

[Unreleased]: https://github.com/ATkingma/KingmaDoc/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ATkingma/KingmaDoc/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/ATkingma/KingmaDoc/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ATkingma/KingmaDoc/releases/tag/v0.1.0
