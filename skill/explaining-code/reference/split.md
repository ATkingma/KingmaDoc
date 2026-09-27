# One document, or functional and technical apart

Contents: Output format: README.md (cover) · Output format: functional.md · 1. Goal and
users · 2. Context · 3. What users can do · 4. Concepts and rules · 5. Glossary ·
Couldn't work out (optional, at most three) · Output format: technical.md.

Used when the user asks for the functional and technical side separately ("split it",
"a functional and a technical document") or `.featuredoc.yml` has
`explain: {documents: split}`. Otherwise write one document (`README.md`) in the chosen
format, and put the functional models in it where the format says.

With `split`, the subject's folder holds three files:

| File            | For                                     | Holds                                                                                 |
| --------------- | --------------------------------------- | ------------------------------------------------------------------------------------- |
| `README.md`     | everyone: the cover page                | key facts, three sentences, links to the two documents                                |
| `functional.md` | product owners, testers, new developers | what it does, for whom, under which rules; no class, table or file names              |
| `technical.md`  | developers and operators                | how it is built and runs: the chosen format (arc42 or c4), minus the functional parts |

Which model goes where (see [models.md](models.md) and [c4-model.md](c4-model.md)):

| Functional                                              | Technical                                               |
| ------------------------------------------------------- | ------------------------------------------------------- |
| C4 system context (it is for everyone; draw it in both) | C4 system context, container, component, code           |
| use case diagram and roles-and-permissions table        | sequence and C4 dynamic diagrams                        |
| user journeys, activity diagrams with swimlanes         | C4 deployment diagram                                   |
| domain model (concepts, multiplicities, no types)       | ER diagram, class and package diagrams, context map     |
| lifecycles as state machines in business words          | state machines with events, guards and actions as coded |
| business rules (`BR-1` …) with where they are enforced  | data flow diagram with trust boundaries                 |
| event flow (what happens, in business events)           | cross-cutting concepts, decisions, quality, risks       |
| glossary                                                | configuration, routes, where to find what               |

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
| **Based on**     | <commit hash (branch)> · <ISO date> · KingmaDoc skill explaining-code 5.6.0 (split) |

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

## 2. Context

```d2
<C4 system context diagram>
```

**Figure 1.** <Who uses it and which systems it works with.>

| Part                     | Role       |
| ------------------------ | ---------- |
| <user / external system> | <one line> |

## 3. What users can do

```d2
<use case diagram>
```

**Figure 2.** <The goals each kind of user has.>

| Who    | May                     | Not allowed               |
| ------ | ----------------------- | ------------------------- |
| <role> | <use cases they may do> | <what is refused, if any> |

### <Main use case or journey>

```d2
<user journey or activity diagram with swimlanes>
```

**Figure 3.** <What the user and the system do, step by step.>

## 4. Concepts and rules

```d2
<domain model: business concepts and multiplicities>
```

**Figure 4.** <The things the system knows about and how they relate.>

| Rule | What it says                        | Enforced where       |
| ---- | ----------------------------------- | -------------------- |
| BR-1 | <one business rule, in plain words> | <screen / API check> |

### Lifecycle of <concept> (optional)

```d2
<state machine in business words>
```

**Figure 5.** <The states a <concept> goes through.>

## 5. Glossary

| Term          | Meaning         |
| ------------- | --------------- |
| <domain word> | <plain meaning> |

## Couldn't work out (optional, at most three)

- <question the code cannot answer>
````

## Output format: technical.md

`technical.md` is the chosen format's output format (arc42 in
[arc42.md](arc42.md), or c4 in [c4.md](c4.md)) with these changes:

- The title is `# <Name>: technical design`, and the first line is
  `Functional side: [functional.md](functional.md).`
- The key facts table and the short introduction are left out (they are on the cover).
- arc42 section 1 becomes one line pointing to `functional.md`, and section 12
  (Glossary) points there too; the c4 format leaves out "In short" and "Terms".
- The functional models (use case, domain model, business rules) are not repeated.
