---
name: explaining-code
description: "Explains existing code with rendered diagrams and short tables, as an arc42 or compact C4 document, one file or split into a functional and a technical design (FO/TO) with a threat model. Fixes code blindness. Scope: a feature, a branch or PR, a whole project, a folder, service or module, or only the classes or files the user names. Use when the user asks to explain, describe, document, map, diagram, draw, visualise or give an overview of existing code or architecture; asks how something works, what it does, how the parts fit together, where something happens, or what a branch, PR, commit or task changed or wants a new pattern in it explained; wants onboarding, a walkthrough, a codebase tour, an architecture or design document, arc42, a functional or technical design (FO, TO, or only one of them), C4, UML, sequence, ER or deployment diagrams of existing code; or no longer understands the code. The request may be in any language. Not for features that are not built yet."
version: 6.1.0
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# Explaining code (KingmaDoc)

Code blindness: the code works, but the developer can no longer say what is there or how
it fits together, often because an agent wrote it. This skill gives that insight back:
**numbered pictures, each decoded by a small table, and almost no prose.**

## When to use this skill

| The user wants…                                | Scope   | Subject name         |
| ---------------------------------------------- | ------- | -------------------- |
| to understand one feature ("the contact form") | feature | `Contact form`       |
| to know what a branch or task changed          | branch  | `branch <branch>`    |
| an overview of a whole project                 | project | `Project`            |
| to understand a folder, service or module      | part    | `<folder or module>` |
| only named classes or files (often from git)   | part    | `<main class>`       |

Each subject has its own folder `docs/explain/<NNNN>-<slug>/README.md` (the explainer,
or its cover page when split) with `img/`; `docs/explain/README.md` lists them.
Explaining a subject again updates its folder: run `kingmadoc explain status` first (the
files changed since the commit in its **Based on** row) and update what they touch.
Name the files you explain in `code spans`: that is what the status compares. For a
feature that is not built yet, use the `kingmadoc` skill (plan mode) instead.

Rules:

- **Always deliver the pictures.** Never end your turn before the explainer is written,
  rendered and `kingmadoc explain check <folder>` passes (Step 6). Never ask first and
  stop: every question (screenshots, what you could not work out) comes at hand-over,
  after the finished document. A failed step is fixed and run again, not skipped.
- **Do not change source code.** Only read code and write the explainer and its images.
- **Explain, don't audit.** No risk lists, code review or suggestions unless asked; a
  limitation only as a plain fact that explains behaviour. Evil user stories and the
  threat model are facts too: what the code does against each misuse, or that nothing
  stops it; never a proposal.
- **Picture, caption, table. No stories.** Every figure has a numbered caption
  (`**Figure 3.** …`, no gaps) and at most three sentences; a table decodes it. Never
  describe a diagram in prose, never paste code as an image, no filler. Where a code
  snippet would explain a class or signature, draw a small UML class diagram instead.
- **Zoom in step by step,** one small diagram per level (at most about fifteen elements).
- **Every figure follows its model's notation** ([reference/c4-model.md](reference/c4-model.md),
  [reference/models.md](reference/models.md)) and passes its checklist: a title, a
  legend, typed and described elements, labelled one-way arrows.
- **Text must match the pictures and the code**: counts, names and arrows from the code,
  with its `path` in the tables. Mark what is not used (an endpoint nothing calls) as a
  plain fact.
- Never invent. What cannot be worked out becomes at most three questions (Step 6).
- **Plain language.** Write in the user's language at secondary vocational (mbo) level:
  short sentences, common words, and the terms the user and the code use. Never coin
  compounds or lofty words (avoid e.g. "consolewerktuig", "gereedschapskist",
  "verenigt", "innerlijke rewriter", "onvoorwaardelijk", "idempotentie",
  "hertypeert"). This holds for table cells, captions and the glossary too.
- **A table when it is clearer.** Figures are not a goal: 26 test cases with
  passes/fails are a table, not a picture.

## Working efficiently

- **Work quietly.** No commentary, file contents or drafts in the chat. Speak only to ask
  (Step 1, Step 6) or to hand over (Step 6).
- **Load on demand.** Read only the "Per section" rules of the format file (the scaffold
  of Step 4 already has its headings and tables), and in the model references only the
  sections of the models you draw: each reference starts with a table of contents.
- **Facts before files.** `kingmadoc explain facts --only <sections>` (e.g. `routes,data`)
  gives just what you need; read source files only for what the facts cannot show.
- **Big codebase** (several services, or more than about 100 source files): let a
  subagent (Claude Code: Explore) read the code and return a compact list of
  containers, components, flows and data with paths (about 1,500 tokens).
- **Fix, don't rewrite.** Change a diagram in its `img/*.d2` file and render again.

## Step 1. Pin down the scope, the format and the documents

**Named classes or files** ("see git, only A, B, C; document this, mainly show the new
pattern"): the scope is exactly those (find them with `git status`, `git diff` and
`git log`; also the uncommitted changes), their direct collaborators only as context.
A focus the user names ("the extension of the new pattern") leads: the first figures
show it (class diagram: what is new or extends what; sequence: how a call flows
through it), the rest stays short.

Decide the scope (table above); if unclear, search, take the most likely candidate and
name the others at hand-over. Act on the request directly, without asking back (any
language):

| The user says, e.g.                                                                 | Documents    | Format                          |
| ----------------------------------------------------------------------------------- | ------------ | ------------------------------- |
| "document this branch", "explain the project"                                       | `single`     | `explain.format`, default arc42 |
| "document it as arc42", "an arc42 of this branch"                                   | `single`     | `arc42`                         |
| "as an FO/TO", "describe this branch with an FO and a TO", "functional and technical design" | `split`      | `explain.format` for the TO     |
| "only an FO", "just the functional design"                                          | `functional` | —                               |
| "only a TO", "just the technical design"                                            | `technical`  | `explain.format` for the TO     |

Otherwise `explain.documents` and `explain.format` in `.featuredoc.yml`, otherwise
**single** (one arc42 document). The formats: `arc42` (default, the twelve sections,
[reference/arc42.md](reference/arc42.md)) or `c4` (compact, [reference/c4.md](reference/c4.md)).

| Documents          | Writes                                                  | Rules in                                 |
| ------------------ | ------------------------------------------------------- | ---------------------------------------- |
| `single` (default) | `README.md`: the whole explainer                        | the format file                          |
| `split` (FO/TO)    | `README.md` (cover), `functional.md` and `technical.md` | [reference/split.md](reference/split.md) |
| `functional` (FO)  | `README.md` (cover) and `functional.md`                 | [reference/split.md](reference/split.md) |
| `technical` (TO)   | `README.md` (cover) and `technical.md`                  | [reference/split.md](reference/split.md) and the format file |

**Models:** all by default, each drawn only when the code has its signal (Step 3);
`explain.models` narrows the list and the request overrides both ("without screens",
"only the threat model").

| Models (names in `explain.models`)                                                                   | Rules in                                              |
| ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `c4_context`, `c4_container`, `c4_component`, `c4_code`, `c4_deployment`, `c4_dynamic`               | [reference/c4-model.md](reference/c4-model.md)        |
| `sequence`, `state_machine`, `er_diagram`, `domain_model`, `class_diagram`, `package_diagram`, `activity`, `user_journey`, `use_case`, `event_flow`, `context_map`, `data_flow`, `algorithm` | [reference/models.md](reference/models.md)            |
| `user_stories`, `screens`, `evil_user_stories`                                                       | [reference/stories.md](reference/stories.md)          |
| `threat_model`                                                                                       | [reference/threat-model.md](reference/threat-model.md) ([reference/threats.md](reference/threats.md) only without KingmaDoc) |

## Step 2. Read the code

```bash
kingmadoc explain facts                 # stack, modules, routes, services, data model
kingmadoc explain facts --base main     # a branch: plus its commits and changed files
```

Draw from the facts and never contradict them: project references and module
dependencies are the arrows, the private modules (dominator tree: all that only one
module leads to) are the components' boundaries, the routes table gives routes and
permissions, the DI services name components, the data model feeds the ER diagram, the
changed files are what a branch explains. (No `explain` command: update KingmaDoc, Step 5.)
For a branch also `git log --oneline <base>..<branch>` and `git diff --stat <base>...<branch>`.

Then follow the code from the entry points (routes, pages, commands, jobs) to the data
and the outside world, and collect what the chosen models need: who uses it and which
systems it talks to; the containers (what must run) and their protocols; deployment
(Dockerfiles, compose, CI, IaC); components and, where hard to follow, their key
classes; the three to five main flows; stored data; status fields, multi-role processes
and events; routes and who may call them; business rules and edge cases with where they
are enforced; configuration; decisions with a stated reason; domain terms; documented
stakeholders and requirements (README, CODEOWNERS, `docs/features/*-plan.md`), the
kinds of tests and what they cover, stated conventions; per actor goal a user story with
its screen and misuse; the security measures the code takes. For a branch: what is new,
changed and removed.

## Step 3. Choose the models and draw them

Write every diagram in **D2** (Step 5 turns them into images).

1. **C4, always:** context and containers; a component diagram per container worth
   opening; deployment when the code has deployment files; code level where it helps
   (always in a TO). Follow [reference/c4-model.md](reference/c4-model.md).
2. **Other models, by what the code has:** the decision table in
   [reference/models.md](reference/models.md) (a `status` field → state machine, more
   than three related tables → ER diagram, several roles in turn → swimlanes …). Only
   clear signals; about eight figures in total.
3. **Stories and screens:** as [reference/stories.md](reference/stories.md) says:
   wireframes first, real screenshots only when the request allows starting the app or
   names its URL (otherwise offer them at hand-over).
4. **Threat model:** write the data flow diagram as `img/threat-model.yml` and run
   `kingmadoc threats img/threat-model.yml`, as [reference/threat-model.md](reference/threat-model.md) says.
5. **Readable in both themes:** every shape with a `fill:` gets a `font-color`, never a
   `font-color` without a fill, never fill white (boundaries and nodes are
   `fill: transparent`), black dots get a grey `stroke`. With `explain.palette: drawio`
   (light mode only) use its colours and render with `--light`
   ([c4-model.md](reference/c4-model.md#palette-drawio)).
6. **Tidy arrows:** `direction: down` (people on top, data stores at the bottom; `right`
   only for timelines and swimlanes), one arrow per pair of shapes with a combined label,
   at most 12 arrows per figure (split it otherwise), labels of at most **four words**,
   protocol in brackets (`reads [JSON/HTTPS]`), on one line (no `\n`); arrows to the
   shapes inside a boundary. For nested deployment nodes, one arrow to the outer node
   instead of one per child.
7. **C4 blocks:** name plus `[type: technology]` only; the description goes into the
   table. Give each block a fixed `width` (250-260) so D2 does not cut the text. No
   `grid-*` inside a C4 boundary: ELK then draws straight lines through the blocks.
8. **Activity with swimlanes and loops** gets unreadable with ELK: draw a state diagram
   (linear; `direction: right` when the user wants it horizontal) or a flowchart
   without lanes instead. For a branch, mark new and
   changed parts by border ([reference/arc42.md](reference/arc42.md#branches-marking-changes)).

## Step 4. Write the explainer

```bash
kingmadoc explain scaffold "<subject name>" [--base main] [--documents split] [--format c4] [--models a,b]
```

It picks the folder (next free ID, never reused; a subject explained before keeps its
folder, like `kingmadoc explain new`), writes the empty documents for the chosen format,
documents and models with the key facts, figure numbers and all headings and tables,
updates the index and prints the paths. Fill it in **one pass per document**: read the
scaffold once, then write the whole document with every `<placeholder>` replaced and the
D2 blocks in place, in a single write (not one edit per placeholder). Delete an optional
part that does not apply, but keep every numbered arc42 section ("_Not documented._",
"_Unchanged._"). A folder that already has
documents is not overwritten: edit those. Without `kingmadoc`, make the folder yourself
(highest number plus one, four digits) and copy the output format of the reference files.

## Step 5. Render the pictures

```bash
kingmadoc render docs/explain/<NNNN>-<slug>/*.md
```

It turns every D2 block into a PNG in `img/`, with an `.svg` (dark mode) and the `.d2`
source next to it, and embeds the PNG in the document as a base64 data URI (`--link`:
a relative link instead; rendering again replaces the image, never duplicates it).
Light mode only: add `--light`. Never convert images yourself.
The first run downloads D2 itself (checksum-verified). Never ask the user to install D2. A diagram D2 rejects: fix its `.d2` file and render again. Always use the latest main: `pip install --pre kingmadoc` (`pipx upgrade kingmadoc
--pip-args=--pre`; from GitHub: `pipx reinstall kingmadoc`); the PyPI release 0.2.0
lacks ELK, `scaffold` and `check`. On Windows the
`kingmadoc.exe` shim can be blocked; run
`py -3 -c "from kingmadoc.cli import main; main()" render …` instead.
No `kingmadoc` at all: render with `d2 --pad 20 --layout elk` if present and link the
SVGs, otherwise say that installing KingmaDoc gives the pictures.

## Step 6. Check and hand it over

```bash
kingmadoc explain check docs/explain/<NNNN>-<slug>
```

It fails while a `<placeholder>` is left, a D2 block is not rendered, a linked image is
missing or a document with figures shows no picture (embedded images count), and warns
when a `[Screen]` wireframe has a text its view (named in the caption) does not have. Fix what it names, render again
and repeat until it passes: the explainer is not done before that. Check every figure
against its model's checklist (end of the model references) as well. Then hand over in at most five lines: the path, one or
two sentences on what the system is, the number of figures, and the "Couldn't work out"
questions (at most three), which you then answer into the explainer. Do not paste the
explainer or its figures into the chat.

VS Code shows the pictures only in its Markdown preview. If `.vscode/settings.json` does
not yet open `docs/explain/` as a preview, Ask once: "Should VS Code open explainers
directly as a preview, with the pictures?" and, on yes, run
`kingmadoc skills install --vscode`. Without that yes, mention Ctrl+Shift+V.
Offer real screenshots there too when the explainer has wireframes: "Shall I start the
app and replace the wireframes with screenshots?"
