# One document, or functional and technical apart (FO/TO)

Contents: Output format: README.md (cover) · Output format: functional.md · 1. Goal and
users · 2. Context · 3. Domain model · 4. What users can do · 5. User stories · 6. Per
user story · 7. Glossary · Couldn't work out (optional, at most three) ·
Output format: technical.md · Rules, permissions and edge cases.

Used when the user asks for the functional and technical side separately ("split it",
"a functional and a technical document", "FO/TO", "functioneel en technisch ontwerp")
or `.featuredoc.yml` has `explain: {documents: split}`. Otherwise write one document
(`README.md`) in the chosen format, and put the functional models in it where the
format says.

With `split`, the subject's folder holds three files; with `functional` (only an FO) or
`technical` (only a TO) it holds the cover and that one document, and the cover's table
lists only that document. The red thread stays: a lone TO still names the `US-n` and
`EUS-n.m` it enforces, a lone FO still names each evil user story's `SM-n` when the
code shows the measure.

| File            | For                                     | Holds                                                                                 |
| --------------- | --------------------------------------- | ------------------------------------------------------------------------------------- |
| `README.md`     | everyone: the cover page                | key facts, three sentences, links to the two documents                                |
| `functional.md` | stakeholders: product owners, users, testers, managers | what it does and for whom, in plain words: no class, table, file or endpoint names, no code terms |
| `technical.md`  | developers only                         | how it is built, enforced and run: the chosen format (arc42 or c4) plus business rules, permissions, edge cases and the threat model |

The test for every line: would a stakeholder without programming knowledge understand
it and care about it? Then it belongs in `functional.md`; otherwise in `technical.md`.

**One red thread** runs through both documents: every **user story** `US-n` gets its own
use case `UC-n`, screen and **evil user stories** `EUS-n.m` in `functional.md`; each evil
user story names the **security measure** `SM-n` that stops it, and `technical.md`'s
threat model lists those measures with where the code enforces them. Number all IDs from
1 without gaps; the same ID means the same thing in both documents.

Which model goes where (see [models.md](models.md) and [c4-model.md](c4-model.md)):

| Functional                                              | Technical                                               |
| ------------------------------------------------------- | ------------------------------------------------------- |
| C4 system context (it is for everyone; draw it in both) | C4 system context, container, component, code           |
| use case diagram and actors                             | sequence and C4 dynamic diagrams                        |
| user stories; per story: use case, screen, evil stories | C4 deployment diagram                                   |
| user journeys, activity diagrams with swimlanes         | ER diagram, class and package diagrams, context map     |
| domain model (concepts, multiplicities, no types)       | state machines with events, guards and actions as coded |
| lifecycles as state machines in business words          | business rules (`BR-1` …) with where they are enforced  |
| event flow (what happens, in business events)           | permissions: roles × routes/actions (RBAC), edge cases  |
| glossary                                                | threat model, security measures (`SM-1` …), sensitive data |
|                                                         | cross-cutting concepts, decisions, configuration, routes |

Number the figures per document (Figure 1, 2 … in each). Each document names the other
in its first line. `kingmadoc render` takes all three files at once.

## Output format: README.md (cover)

```markdown
# <Name>

|                  |                                                                                     |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Scope**        | <feature / branch `<branch>` vs `<base>` / project / part `<path>`>                 |
| **Stack**        | <languages, frameworks, data stores>                                                |
| **Entry points** | <`path`, …>                                                                         |
| **Based on**     | <commit hash (branch)> · <ISO date> · KingmaDoc skill explaining-code 6.1.0 (split) |

<at most three plain sentences: what it is, for whom, what it does>

| Document                           | Read it to know                             |
| ---------------------------------- | ------------------------------------------- |
| [Functional design](functional.md) | what it does, for whom, and its rules       |
| [Technical design](technical.md)   | how it is built, how it runs, where to look |
```

## Output format: functional.md

Leave out optional sections that do not apply.

````markdown
# <Name>: functional design

Technical side: [technical.md](technical.md).

## 1. Goal and users

<at most three plain sentences: what it is for and who uses it>

| Stakeholder (optional) | Role                 | Stake, as documented |
| ---------------------- | -------------------- | -------------------- |
| <name or group>        | <e.g. product owner> | <one line>           |

<optional: "Requirements: [<slug>-plan.md](<path>) (REQ-1 … REQ-n)">

## 2. Context

```d2
<C4 system context diagram>
```

**Figure 1.** <Who uses it and which systems it works with.>

| Part                     | Role       |
| ------------------------ | ---------- |
| <user / external system> | <one line> |

## 3. Domain model

```d2
<domain model: business concepts and multiplicities>
```

**Figure 2.** <The overview: the things the system knows about and how they relate.>

| Concept   | What it is, in plain words |
| --------- | -------------------------- |
| <concept> | <one line>                 |

### Lifecycle of <concept> (optional)

```d2
<state machine in business words>
```

**Figure 3.** <The states a <concept> goes through.>

## 4. What users can do

```d2
<use case diagram: one oval per user story>
```

**Figure 4.** <The goals each kind of user has.>

| Actor  | Type                  | Who they are, in one line |
| ------ | --------------------- | ------------------------- |
| <role> | <primary / secondary> | <description>             |

## 5. User stories

| ID   | As a … | I want …         | So that …                           | Use case |
| ---- | ------ | ---------------- | ----------------------------------- | -------- |
| US-1 | <role> | <goal: verb + object> | <benefit, only if stated; else —> | UC-1     |

## 6. Per user story

### US-1: <verb + object>

#### Use case

| UC-1                 |                                                        |
| -------------------- | ------------------------------------------------------ |
| **Primary actor**    | <role>                                                 |
| **Secondary actor**  | <external system, or —>                                |
| **Preconditions**    | <what is true before, e.g. signed in>                  |
| **Main scenario**    | 1. <actor does …> 2. <system does …> 3. …              |
| **Exceptions**       | <2a. <condition>: the system shows "<message>"; back to 1> |
| **Postconditions**   | <what is true afterwards>                              |

#### Screen

![<screen name>](img/screen-us-1.png)

<or, when no screenshot could be made: a D2 wireframe of the screen from its view code>

**Figure 5.** <Screen name, `<route or window>`: screenshot of the running app (or: wireframe from the view code, not a screenshot).>

#### Activity (optional)

```d2
<activity diagram with swimlanes, when several roles or systems take turns>
```

**Figure 6.** <What the user and the system do, step by step.>

#### Evil user stories

| ID      | Evil user story                                                  | Mitigation                                   |
| ------- | ---------------------------------------------------------------- | -------------------------------------------- |
| EUS-1.1 | As a malicious <role> I want to <misuse US-1> so that <gain>.     | SM-1 <or: _Nothing in the code stops this._> |

## 7. Glossary

| Term          | Meaning         |
| ------------- | --------------- |
| <domain word> | <plain meaning> |

## Couldn't work out (optional, at most three)

- <question the code cannot answer>
````

Per section:

- **3. Domain model** comes early: it is the overview that the use cases and stories
  then walk through. Business words and multiplicities, no types or table names.
- **4–6.** User stories, use cases, screens and evil user stories: see
  [stories.md](stories.md).

## Output format: technical.md

`technical.md` is the chosen format's output format (arc42 in
[arc42.md](arc42.md), or c4 in [c4.md](c4.md)) with these changes:

- The title is `# <Name>: technical design`, and the first line is
  `Functional side: [functional.md](functional.md).`
- The key facts table and the short introduction are left out (they are on the cover).
- Section 5 (Building block view) is complete: C4 level 2 (containers), C4 level 3 (a
  component diagram per container that holds logic) and C4 level 4 (a class or ER
  diagram per key component), as [c4-model.md](c4-model.md) says. In the c4 format the
  same three levels are "Containers", "Components" and a code figure per key component.
- arc42 section 1 becomes one line pointing to `functional.md`, section 4 keeps only its
  Technical context (the Business context is `functional.md`), and section 13
  (Glossary) points there too; the c4 format leaves out "In short" and "Terms".
- The functional models (user stories, use cases, screens, domain model) are not
  repeated; refer to them by ID (`US-1`, `UC-1`).
- The [rules, permissions and edge cases](#rules-permissions-and-edge-cases) are always
  there: in arc42 under section 9, in c4 under "Routes and permissions".
- The [threat model](threat-model.md) is always there: in arc42 as `### Threat model`
  under section 9, in c4 as `## Threat model` before "Where to find what". It lists
  every `SM-n` that the evil user stories in `functional.md` name.

## Rules, permissions and edge cases

For developers: how the code enforces what `functional.md` promises. Also used in a
single arc42 or c4 document (arc42 section 9).

````markdown
### Business rules

| Rule | What it enforces                   | Where (layer, `path`) | For      |
| ---- | ---------------------------------- | --------------------- | -------- |
| BR-1 | <validation or check, as coded>    | `<path>`              | <US-n>   |

### Permissions

| Role   | <route or action> | <route or action> |
| ------ | ----------------- | ----------------- |
| <role> | <allowed / denied / condition, e.g. own data only> | <…> |

<one line: where the check runs (middleware, attribute, policy) and what a denied
request gets (hidden, 403, 404)>

### Edge cases

| Situation                               | What the code does          | Where    |
| --------------------------------------- | --------------------------- | -------- |
| <empty or invalid input, twice at once, a dependency down, cancel or retry> | <behaviour as coded> | `<path>` |
````

Rules: only what the code does (validations, guards, `[Authorize]`/middleware, catch
blocks, unique constraints, locks, retries), each with its `path`; a situation the code
does not handle is a plain fact (_Not handled in the code._), not a proposal.
