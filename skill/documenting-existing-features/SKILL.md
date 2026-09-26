---
name: documenting-existing-features
description: Documents a feature that already exists in the codebase, as built. Finds its code, works out what it really does, and writes a feature document in the KingmaDoc plan format with status "implemented", including C4 diagrams and an implementation map with file and line references. Use when the user asks to document, explain, describe or reverse-engineer an existing feature, module or flow, or wants docs for code written earlier (for example in a previous agent session) that has no plan yet.
version: 1.0.0
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# Documenting existing features (KingmaDoc)

KingmaDoc prevents _code blindness_: code that works, but that nobody can explain any
more. Its `plan` mode documents features before they are built; this skill documents a
feature that **already exists**, as it is built today. The result uses the same format
as a KingmaDoc plan (`docs/features/<slug>-plan.md`), so the same tools work on it
afterwards (the `kingmadoc` skill's verify mode, `kingmadoc verify`, the design models).

## When to use this skill

| The user wants…                                      | Use                                |
| ---------------------------------------------------- | ---------------------------------- |
| a design doc for a feature that is **not built yet** | the `kingmadoc` skill, plan mode   |
| to check built code **against an existing plan**     | the `kingmadoc` skill, verify mode |
| docs for a feature that **exists but has no plan**   | **this skill**                     |

Ground rules:

- **Do not change source code.** This skill only reads code and writes documentation.
- **Describe what the code does, not what it should do.** Every statement about
  behaviour points to the code (`path:line`). Where intent is unclear, write an open
  question instead of guessing.
- Mark everything derived from the code _(inferred)_. Never invent requirements, users
  or systems the code does not show.
- Ask before overwriting an existing document.
- If the `kingmadoc` command is installed (`command -v kingmadoc`), run
  `kingmadoc analyze --json` for the stack, entry points and module dependencies.

## Step 1. Pin down the feature

Get one of: a feature name ("password reset"), a user-visible behaviour, an entry point
(route, CLI command, screen, job), a path, or a commit/PR. If the request is vague,
search first (Step 2) and ask one question with the candidates you found, e.g. "I found
`POST /reset` (api/auth.py) and the `reset-password` CLI command. Which one?".

Read `.featuredoc.yml` if it exists (same settings as the `kingmadoc` skill:
`output_dir`, `project`, `diagram_format`, `extra_designs`). The skill always draws
Mermaid.

## Step 2. Find the code

1. **Entry points:** search for the feature's names and words: routes, CLI commands,
   UI components, message handlers, scheduled jobs. Search case-insensitively and try
   synonyms (`reset`, `forgot`, `recover`).
2. **Follow the flow** from each entry point: the functions and classes it calls, the
   data models it reads or writes, the external services it calls. Stop at shared
   infrastructure (logging, generic helpers, frameworks): mention it, don't document it.
3. **History:** `git log --oneline -S "<symbol>"` and `git log --follow -- <file>` show
   when and why the feature was added. A commit or PR description is the best source
   of intent you have.
4. **Tests** that exercise the feature: they show the expected behaviour and its edge
   cases.
5. **Configuration:** feature flags, environment variables and settings it reads.

Keep a list of every file you use, with the symbols and line ranges that matter: it
becomes the implementation map.

## Step 3. Understand what it does

Answer these from the code; each answer gets a `path:line` reference:

- **Who or what triggers it**, and with what input (validation included)?
- **Main flow**, step by step, and the error paths (what happens on bad input, missing
  data, a failing dependency).
- **Data:** which tables, collections, files or caches it reads and writes.
- **External systems:** APIs, queues, email, payment providers.
- **Permissions:** who may use it (auth checks, roles, guards) and what a denied request
  gets.
- **Tests:** which behaviour is covered and which is not.
- **Loose ends:** `TODO`/`FIXME` comments, disabled code, dead flags, missing error
  handling.

## Step 4. Write the as-built document

Write `<output_dir>/<slug>-plan.md` (default `docs/features/`) in the
[output format](#output-format):

- **Summary:** what the feature does, in one sentence (at most 120 characters).
- **Slug:** the summary in lowercase kebab-case, ASCII only (é → e), at most 40
  characters at a word boundary. Example: `password-reset-via-email`.
- **Scope:** _in scope_ is what the code does (with references); _out of scope_ is what
  it visibly does not do (e.g. "no rate limiting on requests", with the place you
  checked).
- **Assumptions:** what the code relies on (configuration, other services, input
  already validated upstream).
- **Risks:** what you observed: untested paths, missing validation, `TODO`s, secrets in
  code. Mark them _(inferred)_ and point to the code.
- **Diagrams:** a C4 Context diagram (users and external systems) and a C4 Container
  diagram (the containers this feature touches). Mermaid, fenced, every element and
  relationship labelled.
- **Open questions:** everything the code cannot tell: intent, business rules without an
  obvious reason, whether an observed gap is deliberate.
- **Implementation map:** one row per file you used.

If `.featuredoc.yml` enables extra designs (`functional_design`, `domain_design`,
`technical_design`, `security_design`), also write those documents next to the plan
(`<slug>-functional-design.md`, …), filled from the code where it can tell (data
models → ERD and domain model, guards → permissions) and _TODO_ elsewhere.

## Step 5. Check with the user

Show the path, a three-line summary, and the open questions. Ask the user to correct
anything that is wrong: they know the intent, you only know the code. Update the
document with their answers (move answered questions to "Answered while documenting").

Mention the next steps: the document can be checked against the code later with the
`kingmadoc` skill's verify mode, and new work on this feature can start from it.

## Output format

Same headings as a KingmaDoc plan (so every KingmaDoc tool reads it), plus an
implementation map at the end. Text in `<angle brackets>` is filled in.

```markdown
# Feature: <summary>

|               |                                                                            |
| ------------- | -------------------------------------------------------------------------- |
| **Project**   | <project name>                                                             |
| **Status**    | Implemented (as-built)                                                     |
| **Generated** | <ISO date and time> by KingmaDoc skill documenting-existing-features 1.0.0 |

> Documented from the existing code, not from a design. Everything marked _(inferred)_
> comes from reading the code; check it, and answer the open questions.

## One-sentence summary

<what the feature does>

## Scope (in / out)

**In scope**

- <behaviour> (`<path>:<line>`)

**Out of scope**

- <what it visibly does not do> (checked in `<path>`)

## Assumptions

- _(inferred)_ <what the code relies on> (`<path>:<line>`)

## Risks

- _(inferred)_ <observed risk> (`<path>:<line>`)

## C4 Context (Mermaid)

<C4Context diagram>

## C4 Container (Mermaid)

<C4Container diagram>

## Open questions

- [ ] <what the code cannot tell>

**Answered while documenting**

- **<question>** <answer from the user>

## Appendix: codebase context _(inferred)_

- **Tech stack:** <stack>
- **Entry points:** <`path`, …>
- **Config files:** <`path`, …>
- **Test directories:** <`path`, …>

## Appendix: implementation map _(inferred)_

| File     | Role in the feature                                | Key symbols (lines)  | Covered by tests     |
| -------- | -------------------------------------------------- | -------------------- | -------------------- |
| `<path>` | <entry point / flow / data / integration / config> | `<symbol>` (<lines>) | <test file, or _no_> |
```

Omit "**Answered while documenting**" until the user has answered something.
