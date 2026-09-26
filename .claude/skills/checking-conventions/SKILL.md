---
name: checking-conventions
description: Checks changes in the KingmaDoc repository against docs/conventions.md, runs the automatic convention checker, and reviews the manual rules. Use after changing code or docs in this repo, when the convention Stop hook reports violations, or when asked to check conventions. Repo development tool only; not the KingmaDoc product skill.
---

# Checking KingmaDoc conventions

Development tool for **this repository only**. It is not shipped with KingmaDoc and is
separate from the product skill (convention A1).

Rules live in `docs/conventions.md`. The **Rule summary** table there lists every rule
ID with its status and whether it is checked automatically (auto) or by you (manual).

## Workflow

```
- [ ] 1. Run the automatic checker
- [ ] 2. Fix every violation; rerun until it passes
- [ ] 3. Review changed files against the manual rules
- [ ] 4. Update rule statuses in docs/conventions.md if a planned rule was implemented
```

**1. Run the checker** (execute it; don't read it):

```bash
python3 .claude/skills/checking-conventions/scripts/check_conventions.py
```

Output: `path:line: RULE message`, exit code 1 on violations. It also runs `pytest`
(G1), and `ruff`/`mypy --strict` once they are installed in `.venv` (D1/D2).

**2. Fix violations.** Look up the rule ID in `docs/conventions.md` only when the
message isn't enough. Don't suppress a check; if a rule is wrong, change the
convention (and the checker) explicitly and say so.

**3. Manual review.** For files changed in this session (`git status`), check the
rules marked `manual` in the summary table. The most commonly violated ones:

- **E3/E4**: new swappable behavior is a `typing.Protocol` passed in as an argument,
  not a subclass or an `if` chain on type.
- **E1**: new logic that doesn't need I/O is a pure function, called from the shell.
- **F4**: new limits and constants have a one-line reason.
- **G3**: new parsers and transformers get a property-based test (once Hypothesis is added).
- **B4/C2**: template changes keep diagrams in Mermaid and keep inferred content labelled.

Report manual findings as `path:line: RULE problem. fix.`, one line each.

**4. Statuses.** If the change implements a planned rule, set it to `adopted` in both
the summary table and the rule's section. If the rule is now machine-checkable, add
the check to `scripts/check_conventions.py` and mark it `auto`.

## Automatic trigger

`.claude/settings.json` runs the checker in `--hook` mode as a Stop hook after every
agent turn that leaves uncommitted changes. On violations it blocks once and feeds the
report back to the agent; it does not re-block within the same turn.
