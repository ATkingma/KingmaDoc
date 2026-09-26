# Test plan: KingmaDoc on an existing project

A hands-on test of KingmaDoc on a real project you already have (for example one built
in an earlier agent session). It covers the CLI, the extra design documents, both agent
skills, and documenting a feature that already exists. Plan about two hours.

Work through the tests in order; each one lists what to run and what to check. Record
every problem in the [results table](#results) at the end.

## 0. Preparation

- [ ] Pick a project with real code, ideally with a database, some routes or commands,
      and tests. Note which features it has, so you can judge KingmaDoc's output.
- [ ] Start from a clean state on a separate branch, so everything KingmaDoc writes is
      easy to see and to throw away:

  ```bash
  cd <your-project>
  git status                      # should be clean
  git switch -c kingmadoc-test
  ```

- [ ] Install the CLI (Python 3.11+) and check the version:

  ```bash
  pipx install git+https://github.com/ATkingma/KingmaDoc
  kingmadoc --version             # 0.1.1 or later
  ```

- [ ] Install both agent skills into the project (Claude Code; for Cursor, Codex or
      Copilot see the README):

  ```bash
  K=<path to a KingmaDoc checkout>
  mkdir -p .claude/skills/kingmadoc .claude/skills/documenting-existing-features
  cp $K/skill/SKILL.md .claude/skills/kingmadoc/
  cp $K/skill/documenting-existing-features/SKILL.md .claude/skills/documenting-existing-features/
  ```

## 1. Codebase analysis

```bash
kingmadoc analyze
kingmadoc analyze --json > /tmp/analysis.json
```

- [ ] **Languages, entry points, config files, test directories** match the project.
- [ ] **Detected stack** lists the frameworks and databases you know are used, and nothing
      that isn't.
- [ ] **Module dependencies** (Python projects) has a plausible count; nothing is listed
      from `tests/`.
- [ ] It finishes quickly (a few seconds at most for a normal project).

## 2. Plan a new feature (CLI)

Pick a small, realistic feature you might add next.

```bash
kingmadoc init                                   # creates .featuredoc.yml
kingmadoc plan "<one sentence describing the feature>"
```

Answer the questions (or press Enter to skip some).

- [ ] The printed path is `docs/features/<slug>-plan.md` and the slug is readable.
- [ ] The doc has: summary, scope, assumptions, risks, C4 Context, C4 Container, open
      questions (unanswered ones as checkboxes), appendix.
- [ ] The **C4 Container** diagram shows your real source modules; **no test folders**.
- [ ] Open the doc in the GitHub web view or the VS Code Markdown preview: **do the
      diagrams render?** Note where they don't (input for the optional image rendering,
      roadmap WP11).
- [ ] `git status` shows only new files under `docs/features/` and `.featuredoc.yml`.

## 3. Extra design documents

In `.featuredoc.yml`, set `enabled: true` for all four `extra_designs`, then:

```bash
kingmadoc plan "<the same feature>" --no-input --force
```

- [ ] Five files are printed: plan, functional, domain, technical, security design.
- [ ] **Technical design → Dependency graph** (Python): the arrows match how your modules
      really import each other; large projects show packages instead of modules.
- [ ] **Security design → Threat model**: the listed containers and data stores are right.
- [ ] **Domain design** and **permissions**: placeholders are clear about what to fill in.
- [ ] Try `models: [threat_model]` under `security_design`: only that section remains.
- [ ] Optional: set `diagram_format: plantuml` or `d2` and check the diagrams with those
      tools.

## 4. Plan with the agent skill

In your agent (e.g. Claude Code), in the project:

> Plan a new feature: <description>

- [ ] The agent asks up to five clarifying questions.
- [ ] It writes `docs/features/<slug>-plan.md` in the same format as the CLI.
- [ ] It asks for **yes / edit / stop** before touching any code, and changes no code
      when you answer **stop**.

## 5. Document an existing feature

This is the main test for projects from earlier sessions. Pick a feature that exists and
that you know well, so you can judge the result.

> Document the existing <feature name> feature.

- [ ] The agent asks which feature you mean if the name is ambiguous, and shows candidates.
- [ ] It writes `docs/features/<slug>-plan.md` with status **Implemented (as-built)**.
- [ ] **Scope** describes what the code actually does, with `path:line` references.
      Open a few references: do they point at the right code?
- [ ] The **implementation map** lists the files that really make up the feature, and no
      unrelated ones.
- [ ] **Risks** mention real gaps (untested paths, `TODO`s), not generic advice.
- [ ] **Open questions** ask about intent the code cannot tell you.
- [ ] `git status`: no source files changed, only the new document.
- [ ] Repeat for a second feature built in a different part of the code.

## 6. Verify

Make a small change to the feature from test 5 (or leave it as is), then:

> Verify <slug> against the code.

- [ ] The agent (skill verify mode) writes `docs/features/<slug>-verify.md` with
      deviations and the build/test/lint results, and only claims checks it really ran.
- [ ] `kingmadoc verify <slug>` (CLI) writes its work-in-progress placeholder and says so.

## 7. Decision records

Set `adr: {enabled: true}` in `.featuredoc.yml`, then:

```bash
kingmadoc adr "Use <a decision you actually made>" --status accepted
kingmadoc adr "Another decision"
```

- [ ] Files `docs/adr/0001-…md` and `0002-…md`, each with date, status, context, decision
      and consequences.

## 8. Safety checks

- [ ] Everything KingmaDoc wrote is under `docs/` (and `.featuredoc.yml`): `git status`.
- [ ] Set `output_dir: ../outside` and run `plan`: it must refuse with a config error.
- [ ] If the project has a file named `plan_default.md.j2` in its root: it is ignored.

When you are done: `git switch -` and delete the test branch, or keep the useful docs.

## Results

Copy this table into your notes (or an issue) and fill in one row per problem:

| Test | What you did | Expected | What happened | Severity (blocker/major/minor) |
| ---- | ------------ | -------- | ------------- | ------------------------------ |
|      |              |          |               |                                |

Also note what you liked, which diagrams did not render where, and which output you
would actually keep in the project.
