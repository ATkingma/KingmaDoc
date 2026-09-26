---
name: explaining-code
description: Explains existing code with numbered pictures and short tables, so a developer sees at a glance what is there and how it works (fixes code blindness, e.g. after an agent wrote it). Works on any scope - a feature, a branch (what did this branch or task change), a whole project, or a part of one. Writes an arc42 architecture document by default (or a compact C4 zoom-in), with rendered diagrams per C4 level, runtime flows and deployment, each decoded by a table. Use when the user asks to explain, document, map or visualise existing code, a feature, a branch or a project.
version: 4.0.0
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
- **Zoom in step by step,** one small diagram per level (at most about twelve boxes).
  Never one giant diagram.
- **Text must match the pictures.** Counts, names and arrows come from the code, not from
  memory ("2 tables" only if the data figure shows 2).
- **Number without gaps** (Figure 1, 2, 3… in document order). No introductions or
  filler: a section starts with its figure. Never paste code as an image.
- **Mark what is not used** as a plain fact in its table row (an endpoint nothing
  calls, a table nothing reads): that is insight, not an audit.
- Point to code in the tables (`path`), not after every sentence.
- Never invent. If something essential cannot be worked out, ask at most three
  questions (Step 6).

## Step 1. Pin down the scope and the format

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

Read the chosen format file before Step 4.

## Step 2. Read the code

Follow the code from the entry points (routes, pages, commands, jobs) to the data and the
outside world. Collect:

- **Context:** who uses it, and which external systems it talks to.
- **Containers:** the runnable parts (apps, services, databases) and how they talk.
- **Deployment:** what runs where: hosts, containers, ports, CI/CD (Dockerfiles, compose,
  workflow files).
- **Components:** the main modules inside each container that matters; for a component
  that is hard to follow, the few classes that explain it (C4 level 4).
- **Flows:** the three to five main actions and the path each takes.
- **Data:** stored records, keys and relations (models, migrations, schema), limited to
  what the scope touches.
- **Routes and permissions** (web apps and APIs): each endpoint, its handler, and who may
  call it (auth guards, roles, middleware).
- **Configuration:** settings, environment variables and important constants.
- **Decisions** the code or history states a reason for (ADRs, README, commit messages),
  and documented quality goals or known debt; leave out anything you would have to guess.
- **Terms:** domain words and the names the code uses for them, when they differ.
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

**Containers**: the runnable parts and how they talk.

```d2
direction: right
user: <User> {shape: person}
web: <Web app>
api: <API>
db: <Database> {shape: cylinder}
user -> web: <HTTPS>
web -> api: <REST>
api -> db: <SQL>
```

**Deployment**: nodes (servers, cloud services) with the containers they run.

```d2
direction: right
ci: <CI/CD pipeline>
host: <Server or cloud> {
  web: <web container :3000>
  api: <api container :8080>
  db: <database file or service> {shape: cylinder}
}
ci -> host: <builds and deploys>
host.web -> host.api: <internal network>
host.api -> host.db
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

**Code** (C4 level 4, only where it helps): the classes and members that matter; never
getters or setters; keep UI and domain classes apart.

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

**Data**: only the tables the scope touches (say which ones you left out); arrows and
their direction follow the real foreign keys.

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

Write the file from the scope table in the format you picked in Step 1, following its
reference file exactly (sections, figure numbering, tables). Leave out optional
subsections that do not apply; keep every numbered arc42 section, writing
"_Not documented._" or "_Unchanged._" where there is nothing to say.

## Step 5. Render the pictures

An explainer is not finished until its diagrams are pictures. Run:

```bash
kingmadoc render docs/explain/<file>.md
```

It replaces each diagram block with its image (`docs/explain/img/*.svg`) and moves the
D2 source to `docs/explain/img/*.d2`, so the document shows only pictures. To change a
diagram later, edit its `.d2` file and render again. The first time it downloads D2 by
itself (checksum-verified).

- A diagram D2 rejects: fix it and run again.
- `kingmadoc` has no `render` command: it is outdated; ask the user to update it
  (`pipx install --force git+https://github.com/ATkingma/KingmaDoc`), then render.
- `kingmadoc` is not installed at all: render with `d2` if available
  (save each diagram as `docs/explain/img/<file>-<n>.d2`, run
  `d2 --pad 20 <that>.d2 <that>.svg`, and replace the block with
  `![<caption>](img/<file>-<n>.svg)`); otherwise say that installing KingmaDoc gives
  the pictures.

## Step 6. Hand it over

Show the path, the one-paragraph summary and the figures (check the document embeds the
images). Ask the "Couldn't work out" questions, at most three, and update the explainer
with the answers. In VS Code, mention that `kingmadoc skills install --vscode` makes
explainers open as a rendered preview; do not run it without the user's consent.
