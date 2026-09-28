---
name: kingmadoc
description: Generates a Feature Design Doc (plan) before a feature is implemented and a Feature Verification Doc afterwards, with Mermaid C4 diagrams inferred from the codebase. Use when the user asks to plan, design, or scope a new feature before writing code (also "feature design", "technical design", "document over een issue/fix", "ontwerp", "plan", "hoe gaan we dit oplossen", "technisch ontwerp"); for code that already exists, use the explaining-code skill, or to verify, review, or check what was built against its plan. Works without installing anything; uses the kingmadoc CLI when it is available.
version: 1.2.0
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# KingmaDoc

KingmaDoc prevents _code blindness_: the developer (and every later agent session) can
see what a feature is meant to do before it is built, and what was actually built
afterwards, without reading every line of code. You produce two Markdown files per
feature in `docs/features/`: `<slug>-plan.md` and `<slug>-verify.md`.

Contents: [When to use](#when-to-use-this-skill) · [Mode 1: plan](#mode-1-plan) ·
[Mode 2: verify](#mode-2-verify) · [Diagram rules](#diagram-rules) ·
[Output format](#output-format)

## When to use this skill

| Mode       | Use when the user…                                                                     | Output                           |
| ---------- | -------------------------------------------------------------------------------------- | -------------------------------- |
| **plan**   | wants to build, add, design or scope a feature and no code has been written for it yet | `docs/features/<slug>-plan.md`   |
| **verify** | has implemented (part of) a planned feature and wants to know if it matches the plan   | `docs/features/<slug>-verify.md` |

- If the user asks to implement a feature and no plan exists, run **plan** first and
  get approval before changing code.
- If the user says "check", "verify", "review against the plan" or names an existing
  `*-plan.md`, run **verify**.
- If it is unclear which mode is meant, ask one short question.

Ground rules for both modes:

- **Never invent facts.** Everything you derive from the code is marked _(inferred)_;
  everything only the human can know is a `_TODO: …_` placeholder or an open question.
- **Do not change source code** in either mode. You only write the two doc files.
- **Never delete** existing feature docs. If the target file exists, ask before
  overwriting it.
- If the `kingmadoc` command is on `PATH` (`command -v kingmadoc`), prefer it for the
  deterministic parts (see the steps). The docs must look the same either way.

## Mode 1: plan

### Step 1. Read the configuration

Read `.featuredoc.yml` in the project root if it exists. Use these keys (defaults in
brackets); ignore the file if it is absent:

- `output_dir` [`docs/features`]: where docs are written.
- `max_questions` [`5`]: number of clarifying questions (never more than 5).
- `project.name` [project directory name] and `project.description` [empty].
- `analyzer.exclude_dirs` [`.git`, `node_modules`, `.venv`, `venv`, `__pycache__`,
  `dist`, `build`, `*.egg-info`, tool caches], `analyzer.max_files` [`5000`],
  `analyzer.tree_depth` [`3`].
- `diagrams` [`c4_context`, `c4_container`, `class`, `sequence`]: which sections get
  a diagram.
- `diagrams_png` [`embed`]: `embed`, `file` or `off`; see
  [Rendering](reference/diagram-rules.md#rendering).
- `language` [`en`]: language of fixed sentences, notes and captions (headings stay English).
- `extra_designs.functional_design.enabled` / `extra_designs.technical_design.enabled`
  [`false`]: also write a functional and/or technical design doc. By default only the
  plan is written. The request decides directly, without asking back: "FO and TO",
  "FO/TO", "functional and technical design", "split" → both; "only an FO" → the
  functional design; "only a TO" → the technical design (CLI: `--documents split`,
  `functional` or `technical`).
- `extra_designs.<doc>.models` [all]: which models a doc contains. Functional (for
  stakeholders, plain words): `user_stories`, `use_case_diagram`, `use_cases`,
  `screen_designs`, `evil_user_stories`, `user_flows`. Technical (developers only):
  `business_rules`, `permissions`, `edge_cases`, `threat_model`, `dependency_graph`. Models the user names in the request
  win ("only user stories and screens"); with the CLI pass them as `--models a,b`, which
  also switches on the docs that have them.

### Step 2. Analyze the codebase

If `kingmadoc` is installed, run `kingmadoc analyze --json` and use its output for this
step. Otherwise use Glob/Grep (never read the whole codebase):

1. **Files.** Glob `**/*`, skipping the excluded directories. Stop at `max_files`
   and note in the appendix that the analysis is truncated.
2. **Languages.** Count files per extension: `.py` python, `.js/.jsx/.mjs` javascript,
   `.ts/.tsx` typescript, `.go` go, `.rs` rust, `.java` java, `.kt` kotlin, `.rb` ruby,
   `.php` php, `.cs` csharp, `.vb` vb, `.ps1` powershell, `.sql` sql, `.xml` xml,
   `.sh` shell, `.cshtml` razor, `.md` markdown, `.json` json, `.toml` toml,
   `.yml/.yaml` yaml, and so on. Sort by count, highest first.
3. **Top-level directories** that contain files.
4. **Entry points**: files named `main.py`, `app.py`, `__main__.py`, `manage.py`,
   `wsgi.py`, `asgi.py`, `server.py`, `index.{js,ts,tsx}`, `main.{js,ts,tsx,go,rs}`,
   `app.{js,ts}`, `server.{js,ts}`, `Program.cs`, `Main.java`, outside test directories.
5. **Config files** at most two directories deep: `pyproject.toml`, `setup.py`,
   `requirements.txt`, `package.json`, `tsconfig.json`, `go.mod`, `Cargo.toml`,
   `pom.xml`, `build.gradle*`, `Gemfile`, `composer.json`, `*.csproj`, `Dockerfile`,
   `docker-compose.y*ml`, `compose.y*ml`.
6. **Test directories**: outermost directories named `tests`, `test`, `__tests__`,
   `spec` or `specs`.
7. **Stack.** Read the config files and list languages, frameworks and services from
   their dependencies, e.g. `fastapi` → FastAPI, `django` → Django, `react` → React,
   `express` → Express, `psycopg2`/`asyncpg`/`pg`/`github.com/jackc/pgx` or a
   `postgres` image → PostgreSQL, `redis` → Redis, `mongo*` → MongoDB. Confirm
   frameworks with Grep on imports (e.g. `^\s*(from|import)\s+fastapi`). Only list
   what you actually found.
8. **Containers** for the C4 Container diagram: directories with source code
   (`src/<pkg>` counts as `<pkg>`; skip `tests`, `docs`, `examples`, `scripts`, hidden
   directories), at most 6. Technology: first the project files (`.csproj` → C#,
   `.vbproj` → VB.NET, `package.json` → JavaScript/TypeScript, `pyproject.toml` →
   Python), only then the most common extension inside, not counting test data and
   fixtures. If there are none, use one container named after the project, described
   as "Main application".
9. **Open changes**: `git status --short` and `git stash list`; note the ones that
   touch the feature (see the plan format's Appendix).

### Step 3. Ask clarifying questions

Ask the user these questions (at most `max_questions`, in this order), all in one
message, and say they may skip any:

1. What problem does this feature solve, and for whom?
2. Who or what triggers it (end user, scheduled job, external system, ...)?
3. Which external systems, services, or data stores does it interact with?
4. Which existing modules will change? (mention the detected containers)
5. How will you know it works? List the acceptance criteria.

Answers already in the conversation or the request are filled in as a proposal
("Proposal: … — is this right?"), so the user only confirms or corrects them.
If you cannot ask (non-interactive run), or the user skips a question, list it under
**Open questions** instead. Use the answers to fill in scope, assumptions, risks and
the diagrams, but never beyond what the user said or the code shows.

### Step 4. Generate the Feature Design Doc

- **Summary**: the first sentence (ends at `.`/`!`/`?` + capital letter, never at e.g./i.e./etc./vs./cf./approx.),
  whitespace collapsed, at most 120 characters (cut at a word boundary and end with `…`).
- **Slug**: the summary transliterated to ASCII (é→e), lowercase kebab-case, at most 40 characters at a word
  boundary; if non-Latin text leaves nothing, `feature-` + first 8 hex of its SHA-256.
  Example: "Add password reset via email. Links expire…" → `add-password-reset-via-email`.
- Fill every section of the [plan format](reference/formats.md#plan-doc-docsfeaturesslug-planmd) in order.
  Scope, assumptions and risks come from the user's answers; anything not covered stays
  a `_TODO: …_` line. Add answered questions under "Answered while planning".
- **Frontmatter** first (`---` YAML): `kingmadoc: 1`, `feature: <slug>`, `status: draft`,
  `requirements` listing every ID of the Requirements section, and `files_expected` with
  the existing files or folders from answer 4 (`[]` if none). Tools read this block.
- **Requirements**: each acceptance criterion from answer 5 becomes `- **REQ-n**:` in EARS
  (`WHEN <trigger> THE SYSTEM SHALL <response>`, `IF <condition> THEN THE SYSTEM SHALL …`),
  numbered from 1; none given: one `_TODO_` requirement. A vague criterion ("all tests
  pass"): propose concrete EARS requirements and ask for confirmation, rather than one
  vague REQ or invented ones. Under each: `Verified by: <test, test case or command>`
  (or `_TODO_`).
- **Planned changes**: per `files_expected` path what changes and why (the "how" of
  answer 4), one to three lines, no code blocks. Risks and assumptions may add code
  findings marked _(inferred)_.
- **Generated**: the real system time (`date -Iminutes`).
- External systems: those from answer 3, plus systems the code demonstrably uses
  (the latter marked _(inferred)_ below the diagram), as `System_Ext` in the Context
  diagram.
- Follow the [diagram rules](reference/diagram-rules.md).

### Step 5. Write the file and ask for approval

1. Write `<output_dir>/<slug>-plan.md` (ask first if it exists). For each enabled
   extra design, also write `<slug>-functional-design.md`
   ([format](reference/formats.md#functional-design-doc-docsfeaturesslug-functional-designmd)) and/or
   `<slug>-technical-design.md`
   ([format](reference/formats.md#technical-design-doc-docsfeaturesslug-technical-designmd)), in that
   order. Fill in only what the answers and code support; leave the rest as TODOs.
   In the functional design, keep the red thread: one user story per requirement, and
   per story its use case, screen design (a screenshot when the screen already exists)
   and evil user stories, each pointing at a security measure `SM-n` in the technical
   design's threat model. That threat model follows the Microsoft Threat Modeling Tool;
   with the CLI, `kingmadoc threats <file>.yml` generates its threats.
2. Show the paths and a three-line summary (scope, biggest risk, open questions count);
   do not paste the plan into the chat, and do not narrate while you work.
3. Ask the user to reply **yes** (approve), **edit <changes>**, or **stop**. On
   **edit**, update the doc and ask again. On **yes**, run `kingmadoc approve <slug>`
   (with the CLI; otherwise set `status: approved` in the frontmatter and **Status** to
   `Approved`). With the CLI, `kingmadoc check <slug>` validates the plan first.
   Do not change any source code before the plan is approved.

## Mode 2: verify

With the CLI, start with `kingmadoc verify <slug>`: it writes the verify doc with the
changed files, scope and requirement deviations, and sets the plan's status. Add
`--run-checks` only when the user agrees to run the project's commands. Then go through
the steps below to add what it cannot see (behaviour, assumptions, risks).

### Step 1. Find the plan

- If the user gave a slug, use `<output_dir>/<slug>-plan.md`. If they gave a path or a
  feature name, derive the slug from it.
- If no slug was given, Glob `<output_dir>/*-plan.md`. One match: use it. Several:
  ask which one. None: stop and tell the user to run plan mode first.
- If the plan file does not exist, say so, list the slugs that do exist, and stop.
  Do not write a verify doc without a plan.

### Step 2. Read the actual code

1. Read the whole plan doc: its frontmatter (`requirements`, `files_expected`), scope,
   requirements, assumptions, risks, both diagrams, open questions.
2. Find what changed for this feature: `git log --since="<Generated date>" --stat`
   and `git diff` (including uncommitted changes). Without git, use the modules named
   in the plan and the containers in the C4 Container diagram.
3. Read the changed files and the modules the plan says will change. Read only what is
   needed to judge each plan item; do not summarize unrelated code.

### Step 3. Compare and list deviations

Check each item and record every mismatch as a deviation:

- **Scope**: every in-scope item is implemented; no out-of-scope item was built.
- **Requirements**: each `REQ-n` is met (name the code or test), partly met, or not met.
  Files in `files_expected` that were never touched are deviations too.
- **Architecture**: containers and external systems in the code match the C4
  diagrams (new services, databases, queues or APIs count as deviations), and the
  built classes and calls match the class and sequence diagrams (Area: Architecture).
  If the diagrams in the plan changed, render them again.
- **Assumptions**: still true in the code (e.g. "uses the existing auth module").
- **Risks**: each risk is mitigated, accepted, or still open.
- **Open questions**: resolved by the implementation, or still open.

Then run the project's checks, if you can find them (config files, `Makefile`,
`package.json` scripts, CI config): build, tests, lint. Record the exact command and
the result. If a check cannot be run, write `_not run_` and the reason. Never claim a
check passed without running it.

### Step 4. Write the Feature Verification Doc

Write `<output_dir>/<slug>-verify.md` next to the plan in the
[verify format](reference/formats.md#verify-doc-docsfeaturesslug-verifymd) (ask first if it exists). Set
**Status** to `Matches plan`, `Deviations found`, or `Not verified` (when checks could
not run). Show the user the path, the number of deviations, and any failing check.

## Diagram rules

How to draw the Mermaid diagrams (fences, titles, C4 elements, escaping): see
[reference/diagram-rules.md](reference/diagram-rules.md). Read it before drawing.

## Output format

The exact headings of every document this skill writes (plan, verify, functional and
technical design): see [reference/formats.md](reference/formats.md). Read it before
writing a document, and use exactly those headings in that order.
