---
name: explaining-code
description: "Explains existing code with rendered diagrams (C4 in Simon Brown's notation; UML sequence, state, class, activity, use case; ER; data flow) and short tables, as an arc42 or compact C4 document, one file or split into functional and technical. Fixes code blindness, e.g. after an agent wrote the code. Scope: a feature, a branch or PR, a whole project, or a folder, service or module. Use when the user asks to explain, describe, document, map, diagram, draw, visualise or give an overview of existing code or architecture; asks how something works, what it does, how the parts fit together, where something happens, or what a branch, PR, commit or task changed; wants onboarding, a walkthrough, a codebase tour, an architecture or design document, arc42, C4, UML, sequence, ER or deployment diagrams of existing code; or no longer understands the code. The request may be in any language. Not for features that are not built yet."
version: 5.5.0
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# Explaining code (KingmaDoc)

Code blindness: the code works, but the developer can no longer say what is there or how
it fits together, often because an agent wrote it. This skill gives that insight back:
**numbered pictures, each decoded by a small table, and almost no prose.**

## When to use this skill

| The user wants…                                | Scope   | Subject name        |
| ---------------------------------------------- | ------- | ------------------- |
| to understand one feature ("the contact form") | feature | `Contact form`      |
| to know what a branch or task changed          | branch  | `branch <branch>`   |
| an overview of a whole project                 | project | `Project`           |
| to understand a folder, service or module      | part    | `<folder or module>` |

Every subject gets its own folder with a unique ID and its name:
`docs/explain/<NNNN>-<slug>/README.md` (the explainer, or its cover page when split)
and `img/` (its pictures).
`docs/explain/README.md` lists all subjects. Explaining a subject again updates its
folder: first run `kingmadoc explain status`, which lists the files changed since the
commit in its **Based on** row, and update what those changes touch. Name the files you
explain in `code spans` (e.g. in "where to find what"): that is what the status compares.

For a feature that is not built yet, use the `kingmadoc` skill (plan mode) instead.

Rules:

- **Do not change source code.** Only read code and write the explainer and its images.
- **Explain, don't audit.** No risk lists, no code review, no suggestions, unless asked.
  State a limitation only as a plain fact when it explains behaviour.
- **Picture, caption, table. No stories.** Every figure gets a numbered caption
  (`**Figure 3.** …`) and at most three sentences. Tables decode the picture; never
  repeat a table as bullets, and never describe a diagram in prose.
- **Zoom in step by step,** one small diagram per level (at most about fifteen
  elements). Never one giant diagram.
- **Every figure follows its model's notation** ([reference/c4-model.md](reference/c4-model.md)
  for C4, [reference/models.md](reference/models.md) for the others) and passes that
  file's checklist before you hand over: a title, a legend, typed and described
  elements, labelled one-way arrows.
- **Text must match the pictures.** Counts, names and arrows come from the code, not from
  memory ("2 tables" only if the data figure shows 2).
- **Number without gaps** (Figure 1, 2, 3… in document order). No introductions or
  filler: a section starts with its figure. Never paste code as an image.
- **Mark what is not used** as a plain fact in its table row (an endpoint nothing
  calls, a table nothing reads): that is insight, not an audit.
- Point to code in the tables (`path`), not after every sentence.
- Never invent. If something essential cannot be worked out, ask at most three
  questions (Step 6).

## Step 1. Pin down the scope, the format and the documents

Decide the scope (table above). If it is unclear what is meant, search first and ask one
question with the candidates you found.

- **Branch:** `git merge-base <base> <branch>` (base usually `main`), then
  `git log --oneline <base>..<branch>` and `git diff --stat <base>...<branch>`.
- **Project:** if `kingmadoc` is installed, `kingmadoc analyze --json` gives the stack,
  entry points and Python module dependencies.

Pick the format: what the user asks for ("as arc42", "compact", "C4"), otherwise
`explain.format` in `.featuredoc.yml`, otherwise **arc42**.

| Format            | For                                                             | Read                                     |
| ----------------- | --------------------------------------------------------------- | ---------------------------------------- |
| `arc42` (default) | a full architecture picture: the twelve arc42 sections          | [reference/arc42.md](reference/arc42.md) |
| `c4`              | a compact zoom-in: context, containers, components, flows, data | [reference/c4.md](reference/c4.md)       |

Pick the documents the same way: what the user asks for ("one document", "functional
and technical apart"), otherwise `explain.documents`, otherwise **single**.

| Documents          | Writes                                                  | Read                                     |
| ------------------ | ------------------------------------------------------- | ---------------------------------------- |
| `single` (default) | `README.md`: the whole explainer                        | the format file                          |
| `split`            | `README.md` (cover), `functional.md` and `technical.md` | [reference/split.md](reference/split.md) |

Read the chosen files before Step 4.

## Step 2. Read the code

Start from the facts KingmaDoc reads from the code without guessing:

```bash
kingmadoc explain facts                 # stack, modules, routes, services, data model
kingmadoc explain facts --base main     # a branch: plus its commits and changed files
```

Draw from them and never contradict them: the project references and module
dependencies are the arrows between containers and components, the routes and access
table is the source for routes and permissions, the DI services name the components,
the data model is the ER diagram's source, the changed files are what a branch explains. (No `explain` command: update KingmaDoc, see Step 5.)

Then follow the code from the entry points (routes, pages, commands, jobs) to the data and the
outside world. Collect:

- **Context:** who uses it, and which external systems it talks to.
- **Containers:** the runnable parts (apps, services, databases, queues) and how they
  talk (protocols). A container is what must run, not a folder or a package.
- **Deployment:** what runs where: hosts, containers, ports, CI/CD (Dockerfiles, compose,
  workflow files, IaC).
- **Components:** the main groupings behind an interface inside each container that
  matters; for a component that is hard to follow, the few classes that explain it.
- **Flows:** the three to five main actions and the path each takes.
- **Data:** stored records, keys and relations (models, migrations, schema), limited to
  what the scope touches.
- **Lifecycles, processes, events:** status fields and their transitions, steps that
  several roles take in turn, published and handled events.
- **Routes and permissions** (web apps and APIs): each endpoint, its handler, and who may
  call it (auth guards, roles, middleware).
- **Business rules:** validations and checks, in plain words, and where they are enforced.
- **Configuration:** settings, environment variables and important constants.
- **Decisions** the code or history states a reason for (ADRs, README, commit messages),
  and documented quality goals or known debt; leave out anything you would have to guess.
- **Terms:** domain words and the names the code uses for them, when they differ.
- For a branch: what is new, changed and removed, per part.

## Step 3. Choose the models and draw them

Write every diagram in **D2** (Step 5 turns them into images).

1. **C4, always:** a system context and a container diagram; a component diagram per
   container worth opening; a deployment diagram when the code has deployment files.
   Code level, landscape and dynamic diagrams only where they help. Follow
   [reference/c4-model.md](reference/c4-model.md): its abstractions (what is a
   container, what is a component), its notation and its D2 style block.
2. **Other models, by what the code has:** go through the decision table in
   [reference/models.md](reference/models.md) ("a `status` field with transitions" →
   state machine, "more than three related tables" → ER diagram, "several roles in turn"
   → activity diagram with swimlanes, …). Draw only models whose signal is clear; about
   eight figures in total.
3. **Place them** where the format (or, when split, [reference/split.md](reference/split.md))
   says: e.g. arc42 section 6 for flows and lifecycles, section 8 for data and domain.
4. **Readable in dark mode:** the images follow the viewer's light or dark theme. Give
   every shape you fill (`fill:`) a `font-color` too, and black dots a grey `stroke`.
   Never set a `font-color` without a fill (titles, labels: the theme picks the colour),
   and never fill white: boundaries and nodes are `fill: transparent`. Put
   `shape: sequence_diagram` at the top level, or give its container the label `""`.

For a **branch**, mark changes by border, so the C4 colours stay meaningful, and add
both to the legend:

```d2
classes: {
  container: {shape: rectangle; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}}
  new: {style: {stroke: "#2e7d32"; stroke-width: 4}}
  changed: {style: {stroke: "#ef6c00"; stroke-width: 4}}
}
title: "[Container] Webshop - branch feature/invoices" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
vars: {
  d2-legend: {
    n: New in this branch {class: [container; new]}
    c: Changed in this branch {class: [container; changed]}
  }
}
api: "API [Container: ASP.NET Core 10]" {class: [container; changed]}
invoices: "Invoice service [Container: .NET 10]" {class: [container; new]}
api -> invoices: "Requests invoices from\n[HTTPS/JSON]"
```

## Step 4. Write the explainer

Get the subject's folder:

```bash
kingmadoc explain new "<subject name>"   # prints docs/explain/<NNNN>-<slug>/README.md
```

It picks the next free ID (never reused) or, for a subject explained before (same name,
or its ID), returns the existing folder, and updates the index. Without `kingmadoc`,
make the folder yourself: the highest existing number plus one, four digits.

Write that `README.md` in the format you picked in Step 1, following its
reference file exactly (sections, figure numbering, tables). When split, write the
cover `README.md`, `functional.md` and `technical.md` next to each other as
[reference/split.md](reference/split.md) says. Leave out optional subsections that do
not apply; keep every numbered arc42 section, writing "_Not documented._" or
"_Unchanged._" where there is nothing to say.

## Step 5. Render the pictures

An explainer is not finished until its diagrams are pictures. Run:

```bash
kingmadoc render docs/explain/<NNNN>-<slug>/*.md
```

It replaces each diagram block with its image (`img/figure-<n>.svg` for `README.md`,
`img/functional-<n>.svg` and `img/technical-<n>.svg` when split) and moves the D2
source next to it (`.d2`), so the documents show only pictures. Each image has a light
and a dark theme and follows the viewer's (`--light`: light only). To change a diagram
later, edit its `.d2` file and render again. The first time it downloads D2 by itself
(checksum-verified). **Never ask the user to install D2**, even when `d2` is not
on the PATH: `kingmadoc render` does not need it.

- A diagram D2 rejects: fix it and run again.
- `kingmadoc` has no `render` command: it is outdated; ask the user to update it with
  `pipx upgrade kingmadoc` (installed from GitHub: `pipx reinstall kingmadoc`), then render.
- `kingmadoc` is not installed at all: render with `d2` if it happens to be available
  (save each diagram as `img/figure-<n>.d2` in the subject's folder, run
  `d2 --pad 20 <that>.d2 <that>.svg`, and replace the block with
  `![<caption>](img/figure-<n>.svg)`); otherwise say that installing KingmaDoc gives
  the pictures.

## Step 6. Check and hand it over

Go through the checklist of each figure's model (end of
[reference/c4-model.md](reference/c4-model.md) and [reference/models.md](reference/models.md))
and fix what fails. Then show the path, the one-paragraph summary and the figures (check the document embeds the
images). Ask the "Couldn't work out" questions, at most three, and update the explainer
with the answers. In VS Code, mention that `kingmadoc skills install --vscode` makes
explainers open as a rendered preview; do not run it without the user's consent.
