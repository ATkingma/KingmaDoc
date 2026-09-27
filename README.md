# KingmaDoc

**Feature docs for AI coding agents, before and after the code.** When an agent builds a
feature, it's easy to end up with code nobody fully understands: _code blindness_.
KingmaDoc fixes that with two documents per feature. Before implementation, `plan`
analyzes your codebase, asks up to five clarifying questions and writes a plan doc with
scope, assumptions, risks, open questions and C4 architecture diagrams. After
implementation, `verify` compares the code with that plan and lists the deviations and
validation results. Use it as a Python CLI, or with no install at all as a Markdown skill
for Claude Code, Cursor, Codex or GitHub Copilot.

> **Status: 0.2.0.** `plan` is complete.
> `kingmadoc --version` shows the version and the installed commit. `verify` compares the
> code with the plan (changed files, expected files, requirements, containers) and runs
> the project's checks with `--run-checks`. See [CHANGELOG.md](CHANGELOG.md).

## Installation

### pipx (recommended for the CLI)

Requires Python 3.11+.

```bash
pipx install kingmadoc      # from PyPI
pipx upgrade kingmadoc      # later: update to the newest release
```

For the latest commit instead of a release, install from GitHub with
`pipx install git+https://github.com/ATkingma/KingmaDoc` and update it with
`pipx reinstall kingmadoc`; `kingmadoc --version` then shows the commit
(`0.2.1.dev3 (git 1a2b3c4)`). (`pipx install --force` fails on recent pipx versions with
"Failed to create virtual environment" and keeps the old version.) An install from
before 0.2.0 came from GitHub: `pipx uninstall kingmadoc && pipx install kingmadoc`
switches it to the releases.

Then, in your project, install the agent skills; that's all:

```bash
kingmadoc skills install                    # Claude Code (.claude/skills/)
kingmadoc skills install --agent cursor     # or: codex, copilot
```

Run it again after updating KingmaDoc: skill files still as an earlier version installed
them are updated; files you edited are kept (`--force` replaces them too).

Nothing else to install: the first `kingmadoc render` downloads the D2 diagram renderer by
itself (pinned version, checksum-verified; `KINGMADOC_D2_DOWNLOAD=0` turns that off).
VS Code opens a `.md` file as text, which shows no pictures. `kingmadoc skills install`
asks whether VS Code should open explainers (`docs/explain/`) as a rendered preview
instead, so you see the pictures right away (one setting in `.vscode/settings.json`;
`--vscode` / `--no-vscode` answer up front). Without it, press Ctrl+Shift+V in an
explainer. Visual Studio shows a preview by default. The pictures follow VS Code's light
or dark theme.

### pip

```bash
pip install kingmadoc   # into the current environment
```

### Markdown-only (no Python)

Without the CLI, copy the skill files into your project; the agent follows them and
writes the same docs itself (diagrams then stay as text unless `d2` is installed).

| Agent          | Copy                                   | To                                                               |
| -------------- | -------------------------------------- | ---------------------------------------------------------------- |
| Claude Code    | [`skill/SKILL.md`](skill/SKILL.md)     | `.claude/skills/kingmadoc/SKILL.md`                              |
| Cursor         | [`skill/cursor.md`](skill/cursor.md)   | `.cursor/rules/kingmadoc.mdc` (the `.mdc` extension is required) |
| Codex          | [`skill/codex.md`](skill/codex.md)     | append to `AGENTS.md` at the repository root                     |
| GitHub Copilot | [`skill/copilot.md`](skill/copilot.md) | append to `.github/copilot-instructions.md`                      |

```bash
mkdir -p .claude/skills/kingmadoc && cp skill/SKILL.md .claude/skills/kingmadoc/SKILL.md
mkdir -p .cursor/rules && cp skill/cursor.md .cursor/rules/kingmadoc.mdc
cat skill/codex.md >> AGENTS.md
mkdir -p .github && cat skill/copilot.md >> .github/copilot-instructions.md
```

Then ask the agent to "plan <feature>" or "verify <slug>". If the `kingmadoc` CLI is
installed, the skill uses it for the codebase analysis.

**Explaining existing code.** A second skill,
[`skill/explaining-code/SKILL.md`](skill/explaining-code/SKILL.md), explains code that
already exists, with pictures: a feature, a branch (what did this branch or task
change), a whole project, or a part of one. Each subject gets its own folder with a
unique ID, `docs/explain/<NNNN>-<name>/` (the explainer `README.md` plus its `img/`),
listed in `docs/explain/README.md`; explaining it again updates that folder. The
explainer is one document, or on request (or with `explain: {documents: split}`) a
functional and a technical document next to a cover page. It is by default an **arc42** architecture document (the twelve arc42
sections, with C4 diagrams per level, runtime flows and deployment), or a compact C4
zoom-in with `explain: {format: c4}` in `.featuredoc.yml`. Every figure is numbered,
rendered as an image and decoded by a small table. The C4 diagrams follow Simon Brown's
notation (title, legend, element type and technology, labelled one-way arrows); the
agent adds the models the code calls for (UML sequence, state machine, class, activity
with swimlanes, use case, ER, data flow with trust boundaries, context map), each drawn
by its own notation rules. No stories, no audit. Install it next to the first one and ask the agent to "explain <feature / branch /
project>". `kingmadoc skills install` installs it together with the first skill; the
pictures are rendered with `kingmadoc render`; they follow the viewer's light or dark
theme (`--light` for light only).

- The Codex and Copilot files are loaded in **every** session (about 17 KB). Codex
  stops reading `AGENTS.md` files after 32 KiB in total by default
  (`project_doc_max_bytes`). **Lighter alternative:** all three agents also support the
  Agent Skills standard, which loads a skill only when a request needs it. Copy the
  unmodified `skill/SKILL.md` to `.cursor/skills/kingmadoc/`, `.agents/skills/kingmadoc/`
  (Codex) or `.github/skills/kingmadoc/` (Copilot) instead.
- The Claude Code skill's `allowed-tools` includes `Bash`, so it can run git and your
  tests in verify mode without asking. Narrow it if you prefer to approve each command.
- The variants are generated from `skill/SKILL.md`
  (`python3 scripts/build_skill_variants.py`); don't edit them by hand.

## Quick start

```bash
cd your-project
kingmadoc init                      # optional: writes .featuredoc.yml with all defaults
kingmadoc plan "Add password reset via email. Links expire after 30 minutes."
#   answer up to 5 questions (Enter skips; unanswered ones become open questions)
#   → docs/features/add-password-reset-via-email-plan.md
# review the plan, fill in the TODOs, approve it, then let your agent implement it
kingmadoc approve add-password-reset-via-email
kingmadoc verify add-password-reset-via-email [--run-checks]
#   → docs/features/add-password-reset-via-email-verify.md: deviations and check results;
#     the plan's status becomes implemented or partial
kingmadoc analyze --json            # just the codebase analysis, as JSON
```

The plan doc has: one-sentence summary, scope (in/out), assumptions, risks, C4 Context
and C4 Container diagrams, open questions, and an appendix with the detected stack, entry
points and file tree. See [`examples/verify-mode-plan.md`](examples/verify-mode-plan.md)
for a real one, generated on this repository.

More commands:

```bash
kingmadoc plan "…" --no-input --stdout   # no questions, print instead of writing
kingmadoc check add-login                # validate a plan's frontmatter and REQ IDs
kingmadoc approve add-login              # draft -> approved: the gate before code
kingmadoc explain new "Checkout"         # folder for a subject: docs/explain/0001-checkout/
kingmadoc render docs/explain/0001-checkout/README.md   # D2 diagrams -> SVG images
kingmadoc explain status [--check]      # which explainers the code changed under
kingmadoc explain facts --base main      # facts to explain from: data model, branch diff
kingmadoc adr "Use PostgreSQL" --status accepted   # needs adr.enabled
```

## Configuration

All settings live in `.featuredoc.yml` in the project root; every key is optional and
unknown keys are rejected, so typos don't go unnoticed. `kingmadoc init` writes the
file with all defaults and comments; [this repository's
`.featuredoc.yml`](.featuredoc.yml) is exactly that output.

| Key                                       | Default                            | What it does                                                                                                   |
| ----------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `output_dir`                              | `docs/features`                    | Where feature docs are written; must stay inside the project (symlinks resolved) |
| `template`                                | `plan_default.md.j2`               | Plan template: bundled name, or an explicit path like `./my_plan.md.j2` (runs sandboxed)                      |
| `max_questions`                           | `5`                                | Clarifying questions asked by `plan` (0–5)                                                                     |
| `project.name` / `.description`           | directory name / empty             | Used in titles and the C4 Context diagram                                                                      |
| `analyzer.max_files`                      | `5000`                             | Files analyzed (5000 is the maximum)                                                                           |
| `analyzer.tree_depth`                     | `3`                                | Depth of the file tree in the appendix                                                                         |
| `analyzer.max_lines_per_file`             | `2000`                             | Lines read per source file when detecting frameworks from imports (manifests are always read in full)          |
| `analyzer.exclude_dirs`                   | `.git`, `.venv`, `node_modules`, … | Directory names/globs to skip                                                                                  |
| `diagrams`                                | `[c4_context, c4_container]`       | Which C4 diagrams the plan contains                                                                            |
| `diagram_format`                          | `mermaid`                          | `mermaid`, `plantuml` (C4-PlantUML) or `d2`                                                                    |
| `extra_designs.functional_design.enabled` | `false`                            | Also write `<slug>-functional-design.md`: user flows, edge cases, business rules, permissions                  |
| `extra_designs.technical_design.enabled`  | `false`                            | Also write `<slug>-technical-design.md`: database schema, API contracts, error handling, performance, security, and a module dependency graph derived from the code |
| `extra_designs.domain_design.enabled` | `false` | Also write `<slug>-domain-design.md`: domain model, event storming |
| `extra_designs.security_design.enabled` | `false` | Also write `<slug>-security-design.md`: STRIDE threat model (with the inferred elements), who may do what |
| `extra_designs.<name>.models` | all models of that document | Which design models (sections) the document contains, e.g. `[threat_model]` |
| `extra_designs.<name>.template`          | bundled template                   | Template for that document: bundled name or explicit path (runs sandboxed)                                     |
| `adr.enabled`                             | `false`                            | Enable `kingmadoc adr "<title>"`, which writes numbered Architecture Decision Records to `docs/adr/`           |
| `adr.template`                            | `adr.md.j2`                        | ADR template: bundled name or explicit path (runs sandboxed)                                                   |

## Comparison

How KingmaDoc relates to tools with overlapping goals, based on each project's own
documentation (September 2026). "Not documented" means we found no mention, not that
the feature is absent.

|                           | KingmaDoc                                                                                            | [Cline `/deep-planning`](https://docs.cline.bot/features/slash-commands/deep-planning) | [Optimus](https://github.com/oprogramadorreal/optimus-claude) (optimus-claude) | [ProofShot](https://github.com/AmElmo/proofshot)                                 |
| ------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| **Focus**                 | Design doc before, verification doc after                                                            | Implementation plan before coding                                                      | Project setup and quality workflows for Claude Code                            | Visual proof that a UI change works                                              |
| **Before implementation** | Plan doc per feature (`<slug>-plan.md`) with scope, assumptions, risks, open questions               | `implementation_plan.md` in the project root, plus a task with trackable steps         | `brainstorm` skill writes specifications                                       | —                                                                                |
| **Architecture diagrams** | C4 Context and Container, inferred from the code; Mermaid, PlantUML or D2                            | Not documented                                                                         | Not documented                                                                 | —                                                                                |
| **After implementation**  | Verify doc: deviations from the plan, build/test/lint results (skill and CLI) | Not documented                                                                         | Code review, refactoring, TDD and repeated quality passes                      | Browser session recording, screenshots, error report                             |
| **Agents**                | Claude Code, Cursor, Codex, GitHub Copilot; the CLI works with any agent                             | Cline                                                                                  | Claude Code (Codex experimental)                                               | Claude Code, Cursor, Codex, Gemini CLI, Windsurf, others that run shell commands |
| **Install**               | None (Markdown skill), or a Python CLI                                                               | Part of Cline                                                                          | Claude Code plugin                                                             | npm package                                                                      |

They combine well: for example, plan with KingmaDoc, and use ProofShot as the UI
evidence in the verification doc.

## Contributing

Contributions are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers the dev setup,
running the tests, and adding a diagram backend or a template. Coding and
documentation rules are in [`docs/conventions.md`](docs/conventions.md); all docs are
indexed in [`docs/index.md`](docs/index.md). Please open an issue before large changes.

## License

KingmaDoc is released under the MIT License; see [LICENSE](LICENSE).
