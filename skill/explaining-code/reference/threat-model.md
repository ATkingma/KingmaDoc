# Threat model (Microsoft Threat Modeling Tool)

Contents: Output format · How to make it · Rules · Example diagram.

The standard is the **Microsoft Threat Modeling Tool** (TMT, template _SDL TM Knowledge
Base_): its data flow diagram notation, and its report: STRIDE threats per interaction,
each with a state, a priority and a justification. Also used in a single arc42 or c4
document when the code has logins, tokens, personal data, payments, uploads or
webhooks. The report states what the code does against each threat, with a `path`: it
is not an audit and proposes nothing.

## Output format

````markdown
### Threat model

```d2
<data flow diagram in TMT notation: stencils, named flows, trust boundaries>
```

**Figure 7.** <Where data crosses a trust boundary.>

| Element | Stencil (TMT)                           | Trust boundary      | What it does |
| ------- | --------------------------------------- | ------------------- | ------------ |
| <name>  | <External Interactor / Process / Data Store> | <Internet Boundary / outside> | <one line> |

| Not Started | Not Applicable | Needs Investigation | Mitigation Implemented | Total |
| ----------- | -------------- | ------------------- | ---------------------- | ----- |
| 0           | <count>        | <count>             | <count>                | <sum> |

#### Interaction: <flow name> (<source> → <target>)

| # | Threat                                  | Category | Description                                   | State                  | Priority | Justification        |
| - | --------------------------------------- | -------- | --------------------------------------------- | ---------------------- | -------- | -------------------- |
| 1 | Spoofing the <source> External Entity   | Spoofing | <source> may be spoofed by an attacker and this may lead to unauthorized access to <target>. | Mitigation Implemented | High | SM-1 <or why it does not apply> |

#### Security measures

| ID   | Measure                                   | Stops                | Where    |
| ---- | ----------------------------------------- | -------------------- | -------- |
| SM-1 | <e.g. role check on every write endpoint> | <threats #, EUS-n.m> | `<path>` |

#### Sensitive data (optional)

| Data   | Protection level  | How it is protected           | Where    |
| ------ | ----------------- | ----------------------------- | -------- |
| <kind> | <very high … low> | <hashing, HTTPS, access rule> | `<path>` |
````

## How to make it

1. Write the data flow diagram as `img/threat-model.yml` in the subject's folder, with
   the tool's type names (`kingmadoc threats --types` lists them):

   ```yaml
   title: Contact form
   elements:
     - {name: Visitor, type: Human User}
     - {name: Contact API, type: Web Application}
     - {name: Messages, type: SQL Database}
   boundaries:
     - {name: Internet Boundary, type: Internet Boundary, contains: [Contact API, Messages]}
   flows:
     - {name: Form post, from: Visitor, to: Contact API, type: HTTPS}
     - {name: Store message, from: Contact API, to: Messages, type: Binary}
   ```

   Set a property when the code shows it, e.g. `properties: {authenticatesItself: "Yes"}`
   on a signed-in user or `{hasInputSanitizers: "Yes"}` on an app that encodes its
   output; the knowledge base then leaves out the threats they stop.
2. Run `kingmadoc threats img/threat-model.yml --heading "####"`: it prints the diagram
   (D2) and the report with every threat Microsoft's knowledge base generates for each
   flow, with their titles and descriptions. Paste both under `### Threat model`.
   Without KingmaDoc, apply [threats.md](threats.md) by hand in the same way.
3. Fill in each threat from the code, and add the security measures table.

## Rules

- **Diagram, in TMT notation:** External Interactor a rectangle (a person shape for a
  human user), Process a circle, Data Store `stored_data`, Data Flow a one-way arrow
  named by what it carries plus its type (`HTTPS`, `Binary`); a two-way exchange is two
  arrows. Trust boundaries are dashed red boxes named like the tool's (`Internet
  Boundary`, `Machine Trust Boundary`, `Sandbox Trust Boundary`); leave them unfilled.
- **Threats:** keep every generated threat, its title, category and description as the
  knowledge base gives them; never invent threats outside it. Add your own misuse cases
  as evil user stories instead.
- **State** from the code: _Mitigation Implemented_ when a measure is found (the
  justification names its `SM-n`), _Not Applicable_ with the reason (e.g. no user data
  on this flow), _Needs Investigation_ when the code shows no measure. _Not Started_ is
  the tool's default and is not used here; update the summary counts to match.
  **Priority:** High when the flow crosses the Internet Boundary or carries sensitive
  data, Medium when it crosses another boundary, Low otherwise.
- **Evil user stories** from `functional.md` go into the justification of the threat
  they belong to (`SM-2, stops EUS-1.1`). A measure is something the code or its
  configuration does (a check, a header, a rate limit, hashing, HTTPS); the same check on
  several endpoints is one `SM-n`.

## Example diagram

```d2
title: "[Threat model] Contact form" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: right
vars: {
  d2-legend: {
    e: External Interactor
    p: Process {shape: circle}
    s: Data Store {shape: stored_data}
    t: Trust Border Boundary {style: {stroke: red; stroke-dash: 4; fill: transparent}}
  }
}
visitor: Visitor {shape: person}
internet: "Internet Boundary" {
  style: {stroke: red; stroke-dash: 4; fill: transparent}
  api: "Contact API" {shape: circle}
  messages: "Messages" {shape: stored_data}
}
discord: Discord webhook
visitor -> internet.api: "Form post [HTTPS]"
internet.api -> internet.messages: "Store message [Binary]"
internet.api -> discord: "Notification [HTTPS]"
```

