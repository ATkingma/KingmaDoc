# Format: arc42 (default)

Contents: Branches: marking changes · Output format · What changed (branch only) · 1. Introduction and goals · 2.
Constraints · 3. Context and scope · 4. Solution strategy · 5. Building block view · 6.
Runtime view · 7. Deployment view · 8. Cross-cutting concepts · 9. Architecture
decisions · 10. Quality requirements · 11. Risks and technical debt · 12. Glossary ·
Appendix: where to find what · Couldn't work out (optional, at most three).

The default explainer format (`explain: {format: arc42}` in `.featuredoc.yml`): the
twelve sections of the arc42 architecture template, each a figure or a table with a short
explanation. Follow the rules in `../SKILL.md` (numbered figures, tables that decode
them, at most three sentences per figure, no audit).

How the models fit in (draw each as [c4-model.md](c4-model.md) or
[models.md](models.md) says): section 3 is the C4 system context, section 5 holds the
C4 container and component diagrams and, only where it helps, C4 level 4 (code: a UML
class or ER diagram of a key component). Section 6 holds the flows (sequence or C4
dynamic diagrams, activity diagrams, state machines), section 7 the C4 deployment
diagram, section 8 the data (ER), domain model and data flows.

Per section:

- **1. Introduction and goals:** the key facts table and at most three sentences. Then,
  only when the project documents them: the stakeholders (README, CODEOWNERS, docs) and
  the requirements (plan docs in `docs/features/` with their `REQ-n`, a requirements
  file), linked rather than copied. Quality goals only if the project states them.
- **2. Constraints:** fixed choices the code imposes (runtime versions, frameworks,
  hosting), each with where it is set.
- **3. Context and scope:** Figure: context. Then two parts, as a software architecture
  document splits them: **Business context** (for stakeholders: the actors, and with
  `user_stories` on (default) the use case diagram, the user stories table and one
  `#### US-n` per story with its use case, screen and evil user stories, as
  [stories.md](stories.md) says) and **Technical context** (for developers:
  the arrows table with protocols and formats).
- **4. Solution strategy:** at most five rows: the approach and the key technologies, one
  line each; details go to section 9.
- **5. Building block view:** the C4 zoom: Level 1 = C4 level 2 (containers), parts
  table. Level 2 = C4 level 3: one component figure per container that holds logic,
  parts table. Level 3 = C4 level 4: one small class (or ER) figure per key component,
  plus at most three sentences; optional in a single document, required in a split
  `technical.md`.
- **6. Runtime view:** one figure per main action (sequence or C4 dynamic; activity
  with swimlanes when several roles take turns; state machine for a lifecycle), at most
  three sentences each. Name each after the use case it runs (`UC-n`); for a long
  process, one figure per phase (start-up, main loop, output).
- **7. Deployment view:** what runs where: hosts, containers, ports, how it gets there
  (CI/CD). Figure plus a node table.
- **8. Cross-cutting concepts:** one row per concept (data, permissions, validation,
  errors, logging, configuration, security headers …) saying how and where; add the ER
  diagram, the domain model, a data flow diagram with trust boundaries and the
  routes-and-permissions table here when the code has them, and the business rules,
  permissions and edge cases as
  [split.md](split.md#rules-permissions-and-edge-cases) says. When the code has logins,
  tokens, personal data, payments, uploads or webhooks (and always in a split
  `technical.md`), add the threat model as
  [threat-model.md](threat-model.md) says: STRIDE threats and the security measures
  (`SM-n`) the code takes, with where. Add **testability** (which kinds of tests exist,
  where, and what they run against) and, when the repository states them
  (CONTRIBUTING, `.editorconfig`, linter configs, PR templates, the commit history's
  pattern), the **conventions**: code, branches, commits.
- **9. Architecture decisions:** Chosen / Instead of / Why, only with a reason stated in
  the code, docs or history; link ADRs if there are any.
- **10. Quality requirements:** documented quality goals, and the quality scenarios the
  tests cover: per scenario the context (e.g. simple, medium, complex input), the goal it
  checks and how it is tested (`tests/…`, test kind). Tests are facts; do not grade them.
- **11. Risks and technical debt:** only what is documented (README, docs, ADRs, issue
  links, `TODO`/`FIXME` comments), with where it is stated. Do not look for risks or
  judge quality yourself. If nothing is documented, write "_Not documented._".
- **12. Glossary:** domain words and the names the code uses for them.

For a **branch**, add "What changed" at the top and fill the other sections only where
the branch changes them (write "_Unchanged._" otherwise).

## Branches: marking changes

For a branch, mark new and changed parts by their border, so the C4 colours keep their
meaning, and put both in the legend (every format, every C4 level):

```d2
classes: {
  container: {shape: rectangle; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}}
  new: {style: {stroke: "#2e7d32"; stroke-width: 4}}
  changed: {style: {stroke: "#ef6c00"; stroke-width: 4}}
}
title: "[Container] Webshop - branch feature/invoices" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
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

## Output format

Text in `<angle brackets>` is filled in; leave out subsections marked optional.

````markdown
# <Name>: architecture explained

|                  |                                                                                     |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Scope**        | <feature / branch `<branch>` vs `<base>` / project / part `<path>`>                 |
| **Stack**        | <languages, frameworks, data stores>                                                |
| **Entry points** | <`path`, …>                                                                         |
| **Based on**     | <commit hash (branch)> · <ISO date> · KingmaDoc skill explaining-code 6.0.0 (arc42) |

## What changed (branch only)

```d2
<change diagram: new green, changed orange>
```

**Figure 0.** <What this branch added and changed.>

| Part   | Change                              | Where    |
| ------ | ----------------------------------- | -------- |
| <part> | <new / changed / removed: one line> | `<path>` |

## 1. Introduction and goals

<at most three plain sentences: what it is, for whom, what it does>

| Stakeholder (optional) | Role                  | Stake, as documented |
| ---------------------- | --------------------- | -------------------- |
| <name or group>        | <e.g. product owner>  | <one line>           |

<optional: "Requirements: [<slug>-plan.md](<path>) (REQ-1 … REQ-n)">

## 2. Constraints

| Constraint              | Where it is set |
| ----------------------- | --------------- |
| <e.g. .NET 10, Node 22> | `<path>`        |

## 3. Context and scope

```d2
<context diagram>
```

**Figure 1.** <Who uses it and what it talks to.>

### Business context

| Part                     | Role       | Technology |
| ------------------------ | ---------- | ---------- |
| <user / external system> | <one line> | <tech>     |

<with user_stories: use case diagram, user stories table and one "#### US-n: <goal>"
per story (use case, screen, evil user stories), as split.md sections 3 to 5 show>

### Technical context

| From   | To     | What         | How                |
| ------ | ------ | ------------ | ------------------ |
| <part> | <part> | <what flows> | <protocol, format> |

## 4. Solution strategy

| Approach                     | In one line              |
| ---------------------------- | ------------------------ |
| <e.g. server-rendered pages> | <how and why, if stated> |

## 5. Building block view

### Level 1: containers (C4 level 2)

```d2
<containers diagram>
```

**Figure 2.** <The runnable parts and how they talk.>

| Part        | Role       | Technology |
| ----------- | ---------- | ---------- |
| <container> | <one line> | <tech>     |

### Level 2: components of <container> (C4 level 3)

```d2
<components diagram>
```

**Figure 3.** <The parts inside <container>.>

| Part        | Role       | Technology |
| ----------- | ---------- | ---------- |
| <component> | <one line> | `<path>`   |

### Level 3: code of <component> (optional, C4 level 4)

```d2
<class diagram: only the classes and members that matter>
```

**Figure 4.** <The classes that make <component> work.>

<at most three sentences: why these classes, what to notice>

## 6. Runtime view

### <Main action>

```d2
<sequence diagram>
```

**Figure 5.** <What happens when <action>.>

<at most three sentences: what the picture cannot show>

## 7. Deployment view

```d2
<deployment diagram: hosts, containers, ports>
```

**Figure 6.** <Where each part runs.>

| Node                    | Runs         | Port / address |
| ----------------------- | ------------ | -------------- |
| <host or cloud service> | <containers> | <port, URL>    |

## 8. Cross-cutting concepts

| Concept                                                       | How it works | Where    |
| ------------------------------------------------------------- | ------------ | -------- |
| <permissions / validation / errors / logging / configuration / testability> | <one line>   | `<path>` |

### Conventions (optional)

| Convention                    | What the repository states              | Where    |
| ----------------------------- | --------------------------------------- | -------- |
| <code / branches / commits>   | <e.g. `feature/<ticket>-<topic>`, `ADD:`> | `<path>` |

### Threat model (optional)

<data flow figure, STRIDE table and security measures, as split.md says>

## 9. Architecture decisions

| Chosen               | Instead of               | Why                                      |
| -------------------- | ------------------------ | ---------------------------------------- |
| <what the code uses> | <alternative, if stated> | <reason stated in code, docs or history> |

## 10. Quality requirements

<documented quality goals with where they are stated>

| Scenario        | Context                     | Quality goal              | How it is tested        |
| --------------- | --------------------------- | ------------------------- | ----------------------- |
| <e.g. simple input> | <what the input looks like> | <what must hold>      | <test kind, `tests/…`>  |

## 11. Risks and technical debt

<documented risks and debt (docs, TODO/FIXME) with where they are stated, or
"_Not documented._">

## 12. Glossary

| Term          | In the code                |
| ------------- | -------------------------- |
| <domain word> | `<class, table or module>` |

## Appendix: where to find what

| If you want to…            | Look at  |
| -------------------------- | -------- |
| <change the form's fields> | `<path>` |

## Couldn't work out (optional, at most three)

- <question the code cannot answer, needed to understand it>
````
