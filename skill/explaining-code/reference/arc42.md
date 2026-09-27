# Format: arc42 (default)

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

- **1. Introduction and goals:** the key facts table and at most three sentences. Quality
  goals only if the project states them.
- **2. Constraints:** fixed choices the code imposes (runtime versions, frameworks,
  hosting), each with where it is set.
- **3. Context and scope:** Figure: context. Parts table (business context) and arrows
  table (technical context: protocols, formats).
- **4. Solution strategy:** at most five rows: the approach and the key technologies, one
  line each; details go to section 9.
- **5. Building block view:** Level 1: containers, parts table. Level 2: one figure per
  container worth opening, parts table. Level 3 (C4 level 4, optional): one small class
  figure per component that needs it, plus at most three sentences.
- **6. Runtime view:** one figure per main action (sequence or C4 dynamic; activity
  with swimlanes when several roles take turns; state machine for a lifecycle), at most
  three sentences each.
- **7. Deployment view:** what runs where: hosts, containers, ports, how it gets there
  (CI/CD). Figure plus a node table.
- **8. Cross-cutting concepts:** one row per concept (data, permissions, validation,
  errors, logging, configuration, security headers …) saying how and where; add the ER
  diagram, the domain model, a data flow diagram with trust boundaries and the
  routes-and-permissions table here when the code has them.
- **9. Architecture decisions:** Chosen / Instead of / Why, only with a reason stated in
  the code, docs or history; link ADRs if there are any.
- **10. Quality requirements** and **11. Risks and technical debt:** only what is documented
  (README, docs, ADRs, issue links, `TODO`/`FIXME` comments), with where it
  is stated. Do not look for risks or judge quality yourself. If nothing is documented,
  write "_Not documented._".
- **12. Glossary:** domain words and the names the code uses for them.

For a **branch**, add "What changed" at the top and fill the other sections only where
the branch changes them (write "_Unchanged._" otherwise).

## Output format

Text in `<angle brackets>` is filled in; leave out subsections marked optional.

````markdown
# <Name>: architecture explained

|                  |                                                                                     |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Scope**        | <feature / branch `<branch>` vs `<base>` / project / part `<path>`>                 |
| **Stack**        | <languages, frameworks, data stores>                                                |
| **Entry points** | <`path`, …>                                                                         |
| **Based on**     | <commit hash (branch)> · <ISO date> · KingmaDoc skill explaining-code 5.5.0 (arc42) |

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

## 2. Constraints

| Constraint              | Where it is set |
| ----------------------- | --------------- |
| <e.g. .NET 10, Node 22> | `<path>`        |

## 3. Context and scope

```d2
<context diagram>
```

**Figure 1.** <Who uses it and what it talks to.>

| Part                     | Role       | Technology |
| ------------------------ | ---------- | ---------- |
| <user / external system> | <one line> | <tech>     |

| From   | To     | What         | How                |
| ------ | ------ | ------------ | ------------------ |
| <part> | <part> | <what flows> | <protocol, format> |

## 4. Solution strategy

| Approach                     | In one line              |
| ---------------------------- | ------------------------ |
| <e.g. server-rendered pages> | <how and why, if stated> |

## 5. Building block view

### Level 1: containers

```d2
<containers diagram>
```

**Figure 2.** <The runnable parts and how they talk.>

| Part        | Role       | Technology |
| ----------- | ---------- | ---------- |
| <container> | <one line> | <tech>     |

### Level 2: components of <container>

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
| <permissions / validation / errors / logging / configuration> | <one line>   | `<path>` |

## 9. Architecture decisions

| Chosen               | Instead of               | Why                                      |
| -------------------- | ------------------------ | ---------------------------------------- |
| <what the code uses> | <alternative, if stated> | <reason stated in code, docs or history> |

## 10. Quality requirements

<documented quality goals with where they are stated, or "_Not documented._">

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
