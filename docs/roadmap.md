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
| [WP8](#wp8-more-design-models)                                | More design models (UML and others)                                   | to be scoped  | ?    |

## WP1. Machine-readable plans

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

**Tasks**

1. Release workflow: build on a tag, publish to PyPI with trusted publishing (no API
   token), attach the build artefacts to the GitHub release.
2. `pipx install kingmadoc` in the README once published.
3. Supply chain (G7): committed `uv.lock`, `pip-audit` and Ruff's `S` (security) rules
   in CI.

**Done when** tagging `v0.1.2` publishes to PyPI without manual steps.

## WP7. Quality backlog

Small, independent items; pick them up when touching the related code.

- Adopt `ruff format` (D1 lint is adopted; formatting would touch about half the files).
- Walk directories with `os.scandir` (F3).
- Branch coverage with a CI minimum (G2).
- Property-based tests with Hypothesis for the slug, summary and manifest parsers (G3).
- Architecture contracts in `import-linter` (G5), replacing the hand-written E1/E5 checks.

## WP8. More design models

**Goal.** Decide which other models (for example more UML diagram types, data or
threat models) KingmaDoc should generate, and where they fit: in the plan, as an extra
design doc, or as a separate command.

**Status:** not scoped yet. It is the topic of the next design session and becomes one
or more WPs afterwards.
