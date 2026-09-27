# Roadmap

Open functional gaps after 0.1.1, split into work packages (WPs). Each WP can ship on its
own, in the order below; a WP lists what it depends on. Sizes: **S** ≈ a day, **M** ≈ a
few days, **L** ≈ a week or more. Rule IDs (B1, C3, …) refer to
[conventions.md](conventions.md).

| WP                                                            | What                                                                  | Depends on    | Size |
| ------------------------------------------------------------- | --------------------------------------------------------------------- | ------------- | ---- |
| [WP1](#wp1-machine-readable-plans)                            | Machine-readable plans: frontmatter, requirement IDs, approval status | —             | M    |
| [WP2](#wp2-verify-in-the-cli)                                 | Real `verify` in the CLI                                              | WP1           | L    |
| [WP3](#wp3-component-sequence-and-class-diagrams-in-the-plan) | Component, sequence and class diagrams in the plan                    | — (WP1 helps) | L    |
| [WP4](#wp4-split-the-agent-skill)                             | Split the agent skill into `SKILL.md` + `reference/`                  | —             | S    |
| [WP5](#wp5-skill-evaluations)                                 | Evaluations for the skill                                             | WP4           | M    |
| [WP6](#wp6-publishing-and-supply-chain)                       | Publishing on PyPI and supply-chain checks                            | —             | S    |
| [WP7](#wp7-quality-backlog)                                   | Quality backlog (formatter, scandir, coverage, …)                     | —             | S–M  |
| [WP8](#wp8-model-framework) | Model framework: per-document model lists, `security_design` and `domain_design` | — | L |
| [WP9](#wp9-models-derived-from-the-code) | Models derived from the code: dependency graph, ERD, permissions, data flow, threat model, domain model, deployment | WP8 | L |
| [WP10](#wp10-template-models) | Template models: use case, activity, state, BPMN, event storming, user journey, requirements | WP8 (WP1 for requirements) | M |
| [WP11](#wp11-rendered-images-optional) | Optional rendered images (SVG) next to the diagram source | WP8 | M |
| [WP12](#wp12-explain-existing-code) | Explain existing code with pictures (feature, branch, project, part) | WP11 | M |

## WP1. Machine-readable plans

**Status:** done (unreleased): frontmatter, `REQ-n`, `kingmadoc check`, `kingmadoc approve`,
and the skill's format.

**Goal.** A plan doc that tools can read reliably, not just humans.

**Why.** `verify` (WP2) needs to know what was promised. Scraping Markdown headings
breaks as soon as someone edits the text; rules B1, B2 and C1 already describe the
target format.

**Tasks**

1. YAML frontmatter at the top of `<slug>-plan.md` (B2): format version, feature slug,
   `status: draft | approved | implemented | partial`, requirement IDs, expected files.
2. Requirements as `REQ-n` in EARS notation (B1), in a new "Requirements" section,
   filled from the clarifying answers and marked _TODO_ where unknown.
3. `kingmadoc check <slug>`: validate frontmatter and requirement IDs (exit 1 with
   clear messages).
4. `kingmadoc approve <slug>`: set `status: approved` (the approval gate, C1, in the
   CLI; today only the skill has it).
5. Update the skill's output format and the parity tests in `tests/test_skill.py`.

**Done when** a generated plan passes `kingmadoc check`, `approve` flips the status,
and hand-edited plans with a broken frontmatter fail `check` with a useful message.

## WP2. Verify in the CLI

**Status:** done (unreleased): change detection (git), commands (detected or
`verify:` in the config, run only with `--run-checks`), deviations (scope, requirements,
architecture, the approval gate) and the plan's status.

**Goal.** `kingmadoc verify <slug>` compares the code with the plan instead of
writing a placeholder. Today only the agent skill does this.

**Why.** It is half of the product promise ("a verification doc after the code").

**Tasks**

1. **Change detection:** files changed since the plan was generated (git: commits
   after the plan's timestamp plus uncommitted changes; without git: the modules named
   in the plan).
2. **Project commands (C3):** detect build/test/lint commands (pytest, npm scripts,
   cargo, make, CI config) and remember them in `.featuredoc.yml`.
3. **Run the checks** with a timeout and record command, exit code and a short output
   tail. Running commands from an untrusted repository is dangerous: require an
   explicit `--run-checks` flag or a config opt-in.
4. **Deviations:**
   - Architecture drift: re-run the analyzer and compare containers and external
     systems with the plan's diagrams.
   - Scope: expected files (from WP1) that were never touched, and touched files
     outside the plan.
   - Requirements: `REQ-n` IDs without a test or commit that mentions them.
5. **Render** the existing `<slug>-verify.md` format (same headings as the skill) with a
   status of `Matches plan`, `Deviations found` or `Not verified`, and set the plan's
   frontmatter status to `implemented` or `partial`.

**Done when** verifying a small fixture repo reports the planted deviations and check
results, and never runs a command without the opt-in.

## WP3. Component, sequence and class diagrams in the plan

**Goal.** Use the diagram types the backends already render (all three formats) but
`plan` does not generate yet.

**Tasks**

1. **C4 Component** for the container(s) the feature changes: components from the
   module structure (Python packages/modules first, JS/TS files next), relationships
   from imports.
2. **Sequence** skeleton: the actor, the changed containers and the external systems
   from the answers, in the order of the main flow; clearly marked _(inferred)_ and
   _TODO_.
3. **Class model** for touched Python modules from the AST (classes, public methods,
   inheritance); other languages later.
4. New `diagrams:` values (`c4_component`, `sequence`, `class_model`), plan template
   sections, skill format blocks and parity tests.

**Done when** each diagram renders in Mermaid, PlantUML and D2 for a fixture repo, and
the diagrams stay optional through `diagrams:` in the config.

## WP4. Split the agent skill

**Status:** done (unreleased): `SKILL.md` is 184 lines; formats and diagram rules are
in `skill/reference/`; the variants inline them.

**Goal.** Room to grow: `skill/SKILL.md` is at 397 of its 400 lines.

**Tasks**

1. Keep the workflow in `SKILL.md`; move the output formats and diagram rules to
   `skill/reference/*.md`, linked directly from `SKILL.md`, one level deep (A2).
2. Teach `scripts/build_skill_variants.py` to inline the references for Codex and
   Copilot (single-file formats) and keep them separate for Cursor and Claude Code.
3. Keep the heading-parity tests working against the reference files.

**Done when** `SKILL.md` is well under 400 lines, and every variant still contains the
full workflow and formats.

## WP5. Skill evaluations

**Status:** scenarios, checks and runner done (unreleased); see
[evals/README.md](../evals/README.md). Recording results is ongoing.

**Goal.** Know whether agents actually follow the skill (A4), before adding WP1–WP3 to
it.

**Tasks**

1. At least three scenarios in `evals/`: a request, a small fixture repo and the
   expected behaviour (plan written to the right path, questions asked, approval gate
   respected, no source code changed).
2. A script that runs them with and without the skill and reports the differences.
3. Only extend the skill when an eval shows a real failure.

**Done when** the scenarios run with one command and their results are recorded.

## WP6. Publishing and supply chain

**Status:** done (unreleased) except the one-time PyPI setup and the first tag; see
[Releasing](releasing.md).

**Tasks**

1. Release workflow: build on a tag, publish to PyPI with trusted publishing (no API
   token), attach the build artefacts to the GitHub release.
2. `pipx install kingmadoc` in the README once published.
3. Supply chain (G7): committed `uv.lock`, `pip-audit` and Ruff's `S` (security) rules
   in CI.

**Done when** tagging `v0.1.2` publishes to PyPI without manual steps.

## WP7. Quality backlog

Small, independent items; pick them up when touching the related code.

**Status:** branch coverage (minimum 90 %), Hypothesis tests and `import-linter` done
(unreleased); `ruff format` and `os.scandir` open.

- Adopt `ruff format` (D1 lint is adopted; formatting would touch about half the files).
- Walk directories with `os.scandir` (F3).
- Branch coverage with a CI minimum (G2).
- Property-based tests with Hypothesis for the slug, summary and manifest parsers (G3).
- Architecture contracts in `import-linter` (G5), replacing the hand-written E1/E5 checks.

## WP8. Model framework

**Status:** tasks 1 and 2 done (unreleased); tasks 3 and 4 open. The agent skill does
not describe the new documents yet (WP4).

**Goal.** Room for many more models without turning the plan into a wall of diagrams.
Decided in the design session (2026-09-26): models are bundled per document, and each
model can be switched on or off on its own.

| Document | Models |
|---|---|
| `plan` (stays short) | C4 Context, C4 Container |
| `functional_design` | use case, activity, state, BPMN, user journey |
| `technical_design` | ERD, data flow, C4 Deployment, dependency graph, requirements |
| `security_design` (new) | threat model, permission model |
| `domain_design` (new) | domain model, event storming |

**Tasks**

1. Config: `extra_designs.<document>.models: [...]` (defaults: all models of that
   document), validated like `diagrams`.
2. Two new extra designs, `security_design` and `domain_design`, with templates, config
   and skill format blocks (the registry check from 0.1.1 keeps config and code in sync).
3. New diagram kinds in the backend protocol where the three formats can express them
   (flowchart-based data flow, activity, state, ER, deployment); a model a backend cannot
   draw falls back to a table or to Mermaid, never to nothing.
4. Notation: use diagram types that render on GitHub and in common editors (flowchart
   variants) by default. Newer Mermaid types (`usecase`, `eventmodeling`, `swimlane`)
   only through WP11 or an opt-in, because GitHub's Mermaid lags behind.

**Done when** the five documents can be generated with any subset of models, in all
three diagram formats, and the skill describes the same structure.

## WP9. Models derived from the code

**Status:** a (dependency graph: Python in `plan`; JS/TS in `kingmadoc explain facts`) done
(unreleased), plus routes/permissions and .NET services in `explain facts`; b–g open.

**Goal.** The models KingmaDoc can fill in from the code itself; they fight code
blindness best, so they come first. Each item ships on its own, in this order.

| # | Model | Document | Source in the code |
|---|---|---|---|
| a | Dependency graph | technical | Imports between modules (Python first, then JS/TS) |
| b | ERD | technical | ORM models and migrations: SQLAlchemy, Django, Prisma, SQL `CREATE TABLE` |
| c | Permission model: which role may do what | security | Route guards: FastAPI `Depends`, Django `permission_required`/`@login_required`, Express middleware; shown as a role × resource × action matrix |
| d | Data flow diagram with trust boundaries | technical | Containers, data stores and external systems from the analyzer |
| e | Threat model (STRIDE) | security | A STRIDE checklist per element of the data flow diagram (needs d); the human judges each threat |
| f | Domain model | domain | Entities and relationships from the ORM models (shares the parser with b) |
| g | C4 Deployment | technical | Dockerfile, Compose and Kubernetes manifests |

Everything derived is marked _(inferred)_ (B4); what cannot be derived stays _TODO_.

**Done when** each model is correct on a fixture repo per supported framework, and
degrades to a clearly marked placeholder when its source is not found.

## WP10. Template models

**Goal.** Models that depend on intent rather than code: KingmaDoc provides the
structure, filled from the clarifying answers where possible.

- **Use case:** actors and goals from the plan's actors and scope.
- **Activity:** the main flow, with decisions and error paths.
- **State:** states and transitions of the central object; state values from enum or
  status fields when found.
- **BPMN:** a process with lanes per role, approximated with swimlane flowcharts (none of
  the three formats has real BPMN; exporting BPMN XML for bpmn.io is a possible later
  step).
- **Event storming:** domain events, commands, actors and policies, colour-coded.
- **User journey:** the user's steps and experience (Mermaid `journey`).
- **Requirements:** `REQ-n` from WP1 linked to the tests that cover them, which `verify`
  (WP2) can then check.

**Done when** each template renders in all three formats (or its documented fallback)
and the parity tests cover the new format blocks.

## WP11. Rendered images (optional)

**Status:** `kingmadoc render` for D2 done (unreleased), with D2 downloaded automatically
(pinned and verified), so users install nothing extra. Rendering from `plan` itself
(`render_images: true`) and the other formats are open.

**Goal.** Show diagrams as images where Markdown viewers can't render them (older
Mermaid on GitHub, editors without a Mermaid plugin), while keeping the text source.

**Proposal (confirmed 2026-09-26; to be checked in the first test run):**

- Setting `render_images: true`; off by default.
- For each diagram, write an SVG next to the document (for example
  `docs/features/img/<slug>-<model>.svg`) and embed it. The text source stays in the
  document in a collapsible block, because agents cannot read images, and code
  blindness is about agents too.
- Render with a local tool when installed: `d2` (single binary), PlantUML (Java) or
  `mmdc` (Node + headless browser). If none is available, warn and keep text only.
- A rendering service (Kroki) only with an explicitly configured URL: it would send the
  diagram source of possibly private code to a third party.
- `kingmadoc render <slug>` regenerates the images after the text was edited.
- Changes convention B4 ("no rendering step inside KingmaDoc").

**Done when** images are generated and embedded with each installed tool, the text source
is always kept, and nothing is sent anywhere without explicit configuration.

## WP12. Explain existing code

**Status:** agent skill `explaining-code` done (unreleased), after the first test run
showed that an as-built document in the plan format read like an audit (risks, open
questions) instead of giving insight. CLI support (task 3) done
(unreleased): `kingmadoc explain facts` (data model, project references, branch diff)
and `kingmadoc explain status`.

**Goal.** Cure code blindness for code that already exists: show with pictures what is
there and how it works, for a feature, a branch (what it changed), a whole project or a
part of one.

**Tasks**

1. Agent skill `explaining-code`: an explainer in `docs/explain/` with, in this order,
   the big picture, how each main action flows (sequence diagrams), the building blocks,
   the data, what changed (branches), and where to find what. D2 diagrams rendered to
   images with `kingmadoc render` (WP11). No risk list; at most three questions.
2. Tests that keep the format and every D2 example in the skill valid.
3. Later: a CLI command (`kingmadoc explain <scope>`) for the deterministic parts
   (the branch diff, the module graph, the data model from ORM code).

**Done when** a developer who did not write the code can say what is there and how the
main actions flow after reading only "In short" and the pictures.
