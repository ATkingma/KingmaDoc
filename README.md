# KingmaDoc

**Feature docs for AI coding agents, before and after the code.** When an agent builds a
feature, it's easy to end up with code nobody fully understands: _code blindness_.
KingmaDoc fixes that with two documents per feature. Before implementation, `plan`
analyzes your codebase, asks up to five clarifying questions and writes a plan doc with
scope, assumptions, risks, open questions and C4 architecture diagrams. After
implementation, `verify` compares the code with that plan and lists the deviations and
validation results. Use it as a Python CLI, or with no install at all as a Markdown skill
for Claude Code, Cursor, Codex or GitHub Copilot.

> **Status: 0.1.1, first release.** `plan` is complete. The CLI's `verify` is a
> work-in-progress stub that writes a placeholder; the Markdown skill performs the full
> verification. See [CHANGELOG.md](CHANGELOG.md).

## Installation

### pipx (recommended for the CLI)

Requires Python 3.11+.

```bash
pipx install git+https://github.com/ATkingma/KingmaDoc
```

Once KingmaDoc is published on PyPI, this becomes `pipx install kingmadoc`.

Then, in your project, install the agent skills; that's all:

```bash
kingmadoc skills install                    # Claude Code (.claude/skills/)
kingmadoc skills install --agent cursor     # or: codex, copilot
```

Nothing else to install: the first `kingmadoc render` downloads the D2 diagram renderer by
itself (pinned version, checksum-verified; `KINGMADOC_D2_DOWNLOAD=0` turns that off).
`skills install` also makes VS Code open explainers (`docs/explain/`) as a rendered
preview, so you see the pictures right away (`--no-vscode` skips that; Visual Studio
shows a preview by default).

### pip

```bash
pip install git+https://github.com/ATkingma/KingmaDoc   # into the current environment
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
change), a whole project, or a part of one. It writes a short explainer in
`docs/explain/`: by default an **arc42** architecture document (the twelve arc42
sections, with C4 diagrams per level, runtime flows and deployment), or a compact C4
zoom-in with `explain: {format: c4}` in `.featuredoc.yml`. Every figure is numbered,
rendered as an image and decoded by a small table. No stories, no audit. Install it next to the first one and ask the agent to "explain <feature / branch /
project>". `kingmadoc skills install` installs it together with the first skill; the
pictures are rendered with `kingmadoc render`.

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
# review the plan, fill in the TODOs, then let your agent implement it
kingmadoc verify add-password-reset-via-email
#   → docs/features/add-password-reset-via-email-verify.md (placeholder in 0.1.x)
kingmadoc analyze --json            # just the codebase analysis, as JSON
```

The plan doc has: one-sentence summary, scope (in/out), assumptions, risks, C4 Context
and C4 Container diagrams, open questions, and an appendix with the detected stack, entry
points and file tree. See [`examples/verify-mode-plan.md`](examples/verify-mode-plan.md)
for a real one, generated on this repository.

More commands:

```bash
kingmadoc plan "…" --no-input --stdout   # no questions, print instead of writing
kingmadoc render docs/explain/shop.md    # D2 diagrams -> SVG images in the doc
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
| **After implementation**  | Verify doc: deviations from the plan, build/test/lint results (full in the skill; CLI stub in 0.1.x) | Not documented                                                                         | Code review, refactoring, TDD and repeated quality passes                      | Browser session recording, screenshots, error report                             |
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
