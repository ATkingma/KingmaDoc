---
name: explaining-code
description: Explains existing code with numbered pictures and short tables, so a developer sees at a glance what is there and how it works (fixes code blindness, e.g. after an agent wrote it). Works on any scope - a feature, a branch (what did this branch or task change), a whole project, or a part of one. Zooms in step by step - context, containers (what runs where), components, main flows, data - each as a rendered diagram with a table that decodes it. Use when the user asks to explain, document, map or visualise existing code, a feature, a branch or a project.
version: 3.0.0
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# Explaining code (KingmaDoc)

Code blindness: the code works, but the developer can no longer say what is there or how
it fits together, often because an agent wrote it. This skill gives that insight back:
**numbered pictures, each decoded by a small table, and almost no prose.**

## When to use this skill

| The user wants…                                | Scope   | Output                            |
| ---------------------------------------------- | ------- | --------------------------------- |
| to understand one feature ("the contact form") | feature | `docs/explain/<slug>.md`          |
| to know what a branch or task changed          | branch  | `docs/explain/branch-<branch>.md` |
| an overview of a whole project                 | project | `docs/explain/project.md`         |
| to understand a folder, service or module      | part    | `docs/explain/<slug>.md`          |

For a feature that is not built yet, use the `kingmadoc` skill (plan mode) instead.

Rules:

- **Do not change source code.** Only read code and write the explainer and its images.
- **Explain, don't audit.** No risk lists, no code review, no suggestions, unless asked.
  State a limitation only as a plain fact when it explains behaviour.
- **Picture, caption, table. No stories.** Every figure gets a numbered caption
  (`**Figure 3.** …`) and at most three sentences. Tables decode the picture; never
  repeat a table as bullets, and never describe a diagram in prose.
- **Zoom in step by step,** one small diagram per level (at most about twelve boxes):
  context, containers, components, flows, data. Never one giant diagram.
- **Text must match the pictures.** Counts, names and arrows come from the code, not from
  memory ("2 tables" only if the data figure shows 2).
- Point to code in the tables (`path`), not after every sentence.
- Never invent. If something essential cannot be worked out, ask at most three
  questions (Step 6).

## Step 1. Pin down the scope

Decide the scope (table above). If it is unclear what is meant, search first and ask one
question with the candidates you found.

- **Branch:** `git merge-base <base> <branch>` (base usually `main`), then
  `git log --oneline <base>..<branch>` and `git diff --stat <base>...<branch>`.
- **Project:** if `kingmadoc` is installed, `kingmadoc analyze --json` gives the stack,
  entry points and Python module dependencies.

## Step 2. Read the code

Follow the code from the entry points (routes, pages, commands, jobs) to the data and the
outside world. Collect:

- **Context:** who uses it, and which external systems it talks to.
- **Containers:** what runs where (apps, services, databases; the deploy setup such as
  Dockerfiles, compose or CI shows it), and how they talk.
- **Components:** the main modules inside each container that matters.
- **Flows:** the three to five main actions and the path each takes.
- **Data:** stored records, keys and relations (models, migrations, schema).
- **Design choices** the code or history states a reason for (ADRs, README, commit
  messages); leave out choices whose reason you would have to guess.
- For a branch: what is new, changed and removed, per part.

## Step 3. Draw it

Write every diagram in **D2** (Step 5 turns them into images). Labels in plain words,
arrows labelled with what flows.

**Context**: people, the system as one box, external systems.

```d2
direction: right
user: <User> {shape: person}
system: <System>
external: <External service>
user -> system: <uses>
system -> external: <sends data to>
```

**Containers**: what runs where; put deployed units inside the host or cloud they run on.

```d2
direction: right
user: <User> {shape: person}
host: <Server or cloud> {
  web: <Web app>
  api: <API>
  db: <Database> {shape: cylinder}
}
user -> host.web: <HTTPS>
host.web -> host.api: <REST>
host.api -> host.db: <SQL>
```

**Components** of one container (one figure per container worth zooming into).

```d2
direction: down
api: <API container> {
  routes: <Routes>
  service: <Service>
  repo: <Repository>
}
api.routes -> api.service -> api.repo
```

**A flow**: one sequence diagram per main action.

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

**Important classes** (optional, only the members that matter; never getters/setters).

```d2
controller: <Controller> {
  shape: class
  "+send(request)": <Response>
  "-minFillTime": int
}
store: <Store> {
  shape: class
  "+save(message)": void
}
controller -> store: <uses>
```

**Data**: tables with keys; the relations as arrows.

```d2
user: <User> {
  shape: sql_table
  id: int {constraint: primary_key}
  email: string
}
order: <Order> {
  shape: sql_table
  id: int {constraint: primary_key}
  user_id: int {constraint: foreign_key}
}
order.user_id -> user.id
```

For a **branch**, colour the changes: new parts green, changed parts orange.

```d2
api: <API>
new: <New service> {style.fill: "#d4f7d4"}
changed: <Changed module> {style.fill: "#ffe8c2"}
api -> new: <new call>
api -> changed
```

## Step 4. Write the explainer

Write the file from the scope table in the [output format](#output-format). Number the
figures in order (`**Figure 1.**` …). After a context, containers or components figure,
add the **parts table** (Part / Role / Technology) and the **arrows table** (From / To /
What / How). After a flow figure, at most three sentences for what the picture cannot
show (error paths, timing). For a **project**, "How it works" has one flow per main
feature; for a **branch**, fill in "What changed". Leave out optional sections that do
not apply.

## Step 5. Render the pictures

An explainer is not finished until its diagrams are pictures. Run:

```bash
kingmadoc render docs/explain/<file>.md
```

It writes `docs/explain/img/*.svg`, puts each image above its diagram and folds the
source; the first time it downloads D2 by itself (checksum-verified).

- A diagram D2 rejects: fix it and run again.
- `kingmadoc` has no `render` command: it is outdated; ask the user to update it
  (`pipx install --force git+https://github.com/ATkingma/KingmaDoc`), then render.
- `kingmadoc` is not installed at all: render with `d2` if available
  (`d2 --pad 20 <n>.d2 docs/explain/img/<file>-<n>.svg`, then
  `![<caption>](img/<file>-<n>.svg)` above the block); otherwise say that installing
  KingmaDoc gives the pictures.

## Step 6. Hand it over

Show the path, "In short" and the figures (check the document embeds the images). In VS
Code, `kingmadoc skills install` makes explainers open as a rendered preview. Ask the
"Couldn't work out" questions, at most three, and update the explainer with the answers.

## Output format

Text in `<angle brackets>` is filled in.

````markdown
# <Name>: <what it is, in a few words>

|                  |                                                                             |
| ---------------- | --------------------------------------------------------------------------- |
| **Scope**        | <feature / branch `<branch>` vs `<base>` / project / part `<path>`>         |
| **Stack**        | <languages, frameworks, data stores>                                        |
| **Entry points** | <`path`, …>                                                                 |
| **Based on**     | <commit hash (branch)> · <ISO date> · KingmaDoc skill explaining-code 3.0.0 |

## In short

<at most three plain sentences>

## Context

```d2
<context diagram>
```

**Figure 1.** <Who uses it and what it talks to.>

| Part                     | Role       | Technology |
| ------------------------ | ---------- | ---------- |
| <User / external system> | <one line> | <tech>     |

## Containers

```d2
<containers diagram>
```

**Figure 2.** <What runs where.>

| Part        | Role       | Technology   |
| ----------- | ---------- | ------------ |
| <container> | <one line> | <tech, port> |

| From        | To          | What         | How        |
| ----------- | ----------- | ------------ | ---------- |
| <container> | <container> | <what flows> | <protocol> |

## Components

### <Container name>

```d2
<components diagram>
```

**Figure 3.** <The parts inside <container>.>

| Part        | Role       | Technology |
| ----------- | ---------- | ---------- |
| <component> | <one line> | `<path>`   |

## How it works

### <Main action>

```d2
<sequence diagram>
```

**Figure 4.** <What happens when <action>.>

<at most three sentences: what the picture cannot show>

## Data (optional)

```d2
<data diagram>
```

**Figure 5.** <The stored data: <n> tables.>

## What changed (branch only)

```d2
<change diagram: new green, changed orange>
```

**Figure 6.** <What this branch added and changed.>

| Part   | Change                              | Where    |
| ------ | ----------------------------------- | -------- |
| <part> | <new / changed / removed: one line> | `<path>` |

## Design choices (optional)

| Chosen               | Instead of               | Why                                      |
| -------------------- | ------------------------ | ---------------------------------------- |
| <what the code uses> | <alternative, if stated> | <reason stated in code, docs or history> |

## Where to find what

| If you want to…            | Look at  |
| -------------------------- | -------- |
| <change the form's fields> | `<path>` |

## Couldn't work out (optional, at most three)

- <question the code cannot answer, needed to understand it>
````
