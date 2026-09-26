---
name: explaining-code
description: Explains existing code with pictures, so a developer understands what is there and how it works (fixes code blindness, e.g. after an agent wrote it). Works on any scope the user wants insight into - a feature, a branch (what did this branch or task change), a whole project, or a part of one. Writes a short explainer in docs/explain/ with rendered D2 diagrams - the big picture, how each main action flows, the building blocks, the data - and a where-to-find-what table. Use when the user asks to explain, document, map or visualise existing code, a feature, a branch or a project.
version: 2.0.0
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# Explaining code (KingmaDoc)

Code blindness: the code works, but the developer can no longer say what is there or how
it fits together, often because an agent wrote it. This skill gives that insight back
with **pictures first and short explanations**, for whatever the user points at.

## When to use this skill

| The user wants…                                | Scope   | Output                            |
| ---------------------------------------------- | ------- | --------------------------------- |
| to understand one feature ("the contact form") | feature | `docs/explain/<slug>.md`          |
| to know what a branch or task changed          | branch  | `docs/explain/branch-<branch>.md` |
| an overview of a whole project                 | project | `docs/explain/project.md`         |
| to understand a folder, service or module      | part    | `docs/explain/<slug>.md`          |

For a feature that is not built yet, use the `kingmadoc` skill (plan mode) instead.

Ground rules:

- **Do not change source code.** Only read code and write the explainer and its images.
- **Explain, don't audit.** Describe what the code does and how the parts fit together.
  No risk lists, no code review, no improvement suggestions, unless the user asks.
  Mention a limitation only when it is needed to understand the behaviour, stated as a
  plain fact ("the database is recreated on every deploy").
- **Pictures carry the explanation.** Text explains the picture next to it; it does not
  repeat it. Aim for about 150 lines of text in total, diagram sources excluded.
- **Point to code sparingly:** in the where-to-find-what table and where a reader needs
  it, not after every sentence.
- Never invent anything the code does not show. If something essential cannot be worked
  out, ask at most three questions (Step 6).

## Step 1. Pin down the scope

Decide which scope the request is (table above). If it is unclear which feature, branch
or folder is meant, search first and ask one question with the candidates you found.

- **Branch:** find the base (`git merge-base <base> <branch>`, base usually `main`), then
  `git log --oneline <base>..<branch>` and `git diff --stat <base>...<branch>`.
- **Project:** list the main parts (apps, services, packages) and the user-visible
  features. If the `kingmadoc` CLI is installed, `kingmadoc analyze --json` gives the
  stack, entry points and Python module dependencies.

## Step 2. Read the code

Follow the code from the entry points (routes, pages, CLI commands, jobs, handlers)
through the calls to the data and the external systems. For each scope, collect:

- the **parts** (containers, services, modules, components) and how they talk;
- the **main actions**: what a user or system does, and the path it takes through the
  parts (pick the three to five that matter most);
- the **data** that is stored, and where;
- the files a developer would open first for each part and action.

For a branch, also collect what is new, changed and removed, grouped by part.

## Step 3. Draw it

Write the diagrams in **D2** (they are rendered to images in Step 5). One idea per
picture, at most about twelve boxes, labels in plain words, arrows labelled with what
flows. The four kinds you need:

The **big picture**: people, the system's parts, the outside world.

```d2
direction: right
visitor: Visitor {shape: person}
system: <System> {
  web: <Web app>
  api: <API>
  db: <Database> {shape: cylinder}
}
external: <External service>
visitor -> system.web: <uses>
system.web -> system.api: <calls>
system.api -> system.db: <stores>
system.api -> external: <notifies>
```

**How it works**: one sequence diagram per main action.

```d2
shape: sequence_diagram
user: User
web: <Web app>
api: <API>
db: <Database>
user -> web: <fills in the form>
web -> api: <POST /contact>
api -> db: <save message>
api -> web: <200 OK>
web -> user: <shows a thank-you message>
```

**Building blocks**: the modules or components and their dependencies.

```d2
direction: down
ui: <Pages> {
  home: <Home page>
  form: <Contact form>
}
server: <Server> {
  route: <API route>
  service: <Mail service>
}
ui.form -> server.route: <submit>
server.route -> server.service
```

**Data**: the stored records and their relations.

```d2
message: <Message> {
  shape: sql_table
  id: int {constraint: primary_key}
  email: string
  created_at: datetime
}
```

For a **branch**, mark what changed: new parts green, changed parts orange.

```d2
api: <API>
new: <New service> {style.fill: "#d4f7d4"}
changed: <Changed module> {style.fill: "#ffe8c2"}
api -> new: <new call>
api -> changed
```

## Step 4. Write the explainer

Write the file from the table in "When to use" in the [output format](#output-format):

- **In short:** three to five plain sentences a newcomer understands.
- **The big picture** and **Building blocks:** one diagram each, one line per part.
- **How it works:** one `###` per main action: its diagram and two to four sentences.
- **Data:** the data diagram, or "Stores no data."
- **What changed:** only for a branch: the change diagram and the changes per part.
- **Where to find what:** about ten rows, "If you want to…" → "Look at".
- **Couldn't work out:** only if needed, at most three items; otherwise leave it out.

For a **project**, "How it works" gets one `###` per feature, each with a one-line
explanation and its main flow; point to per-feature explainers when they exist.

## Step 5. Render the pictures

Turn the D2 blocks into images that every Markdown viewer shows:

- If `kingmadoc` is installed: `kingmadoc render docs/explain/<file>.md`. It writes
  `docs/explain/img/*.svg`, puts each image above its diagram and folds the source.
- Otherwise, if `d2` is installed: for each diagram, save it as
  `docs/explain/img/<file>-<n>.d2`, run `d2 --pad 20 <that>.d2 <that>.svg`, and put
  `![<section title>](img/<file>-<n>.svg)` above the diagram block.
- If neither is installed: keep the D2 blocks and tell the user to install D2
  (https://d2lang.com/tour/install) and run `kingmadoc render` later.

Fix any diagram D2 rejects before handing over.

## Step 6. Hand it over

Show the path, the "In short" text and the images you rendered. If there are
"Couldn't work out" questions, ask them (at most three) and update the explainer with
the answers. Offer to explain another scope or to go deeper into one action.

## Output format

Text in `<angle brackets>` is filled in; leave out sections marked optional when they
do not apply.

````markdown
# <Name>: <what it is, in a few words>

|               |                                                                                |
| ------------- | ------------------------------------------------------------------------------ |
| **Scope**     | <feature / branch `<branch>` compared with `<base>` / project / part `<path>`> |
| **Based on**  | <commit hash (and branch)>                                                     |
| **Generated** | <ISO date and time> by KingmaDoc skill explaining-code 2.0.0                   |

> What is there and how it works, explained from the code. Pictures first; the diagram
> sources are folded below each picture.

## In short

<three to five plain sentences>

## The big picture

```d2
<big-picture diagram>
```

- **<Part>:** <what it does, one line>

## How it works

### <Main action, e.g. "Sending the contact form">

```d2
<sequence diagram of this action>
```

<two to four sentences>

## Building blocks

```d2
<building-blocks diagram>
```

## Data (optional)

```d2
<data diagram>
```

## What changed (branch only)

```d2
<change diagram: new green, changed orange>
```

- **<Part>:** <what changed and why it matters>

## Where to find what

| If you want to…            | Look at             |
| -------------------------- | ------------------- |
| <change the form's fields> | `<path>` (<symbol>) |

## Couldn't work out (optional, at most three)

- <question the code cannot answer, needed to understand it>
````
