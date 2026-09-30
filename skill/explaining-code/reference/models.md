# Models beyond C4: pick them by what the code has

Contents: Which model for which code · Rules for every model · Sequence diagram (UML) ·
State machine (UML) · ER diagram (crow's foot) · Class diagram and domain model (UML) ·
Package diagram · Activity diagram with swimlanes (UML / BPMN style) · Use case diagram
(UML) · Data flow diagram with trust boundaries · Event flow (event storming colours) ·
Context map (DDD) · Algorithm (flowchart, trace table, formula) · Review checklist.

C4 ([c4-model.md](c4-model.md)) shows structure, deployment and runtime. Everything
else (data, lifecycles, processes, domain, security-relevant data flows) needs its own
model. Pick models from the signals in the code; skip a model whose signal is weak and
never invent content to fill one. Keep the whole explainer to about eight figures.

## Which model for which code

| If the code has…                                                                  | Add                                     | Kind       | arc42 section |
| --------------------------------------------------------------------------------- | --------------------------------------- | ---------- | ------------- |
| HTTP or RPC handlers, clients, callbacks crossing three or more parts             | Sequence diagram per key action         | technical  | 7             |
| A `status` or `state` field with transition methods, guards on it, an FSM library | State machine per entity                | both       | 7 or 9        |
| Migrations, ORM models or a schema with more than three related tables            | ER diagram (crow's foot)                | technical  | 9             |
| Entity or aggregate classes that carry business rules                             | Domain model (conceptual classes)       | functional | 9             |
| An interface or protocol with several implementations, a plugin registry          | UML class diagram of that part          | technical  | 6 (level 3)   |
| Many packages, layering or import rules                                           | Package (dependency) diagram            | technical  | 6 or 9        |
| Several roles acting in turn, approval steps, a workflow engine, queued steps     | Activity diagram with swimlanes         | both       | 7             |
| Routes of a UI, wizards, multi-step forms                                         | User journey (flowchart)                | functional | 7             |
| Several user types with different permissions                                     | Use case diagram + permissions table    | functional | 4             |
| Event classes, publish/subscribe, handlers, sagas                                 | Event flow (event storming colours)     | both       | 7             |
| Several services or modules with their own model, adapters, upstream APIs         | Context map (DDD)                       | technical  | 4 or 9        |
| Logins, tokens, personal data, payments, uploads, webhooks                        | Data flow diagram with trust boundaries | technical  | 9             |
| A complex function with more than three branches, a batch job with retries        | Flowchart                               | technical  | 7             |
| An algorithm: pathfinding, scheduling, pricing, ranking, recursion, nested loops    | Algorithm (flowchart + trace + formula) | technical  | 9             |

Tie-breakers: one caller-callee chain is a sequence; several roles taking turns are
swimlanes; the lifecycle of one thing is a state machine. Prefer one clear figure over
two overlapping ones. ArchiMate only if the project already uses it.

## Rules for every model

- A title `"[<Model>] <scope>"` (e.g. `[State machine] Order`), placed like the C4
  titles, and a `d2-legend` whenever colours, line styles or shapes carry meaning.
- Names are the names the code uses (class, table, status value), so the reader can
  search for them; the table under the figure gives the `path`.
- Quote every label that contains `[`, `]`, `:`, `{`, `}`, `;` or `#` (D2 fails on them
  otherwise).
- D2 draws a `source-arrowhead` only on a two-headed edge (`<->`); on `->` it is silently
  dropped. So ER cardinality uses `<->` with both arrowheads set, and a composition
  diamond is the `target-arrowhead` of an arrow from the part to the whole.
- Only what the scope touches; say in the caption what was left out.

## Sequence diagram (UML)

Rules: participants left to right in the order they are first called; solid arrow =
call or message, **dashed arrow = reply**; label calls with the operation
(`POST /orders`, `save(order)`); alternatives and loops as a group named
`alt [condition]`, `opt [condition]` or `loop [condition]`. Draw the happy path, plus
an error path only when it explains behaviour.

Lifelines, one per code element:

- One lifeline is one class, one file or one external system. Never put two classes, two
  files or two scripts on one lifeline: no `DatasetService / DashboardService`, no
  `Endpoints` for two endpoint classes, no `api` for a whole layer. When a flow passes
  through two classes of the same layer, draw both, each with its own calls.
- The only exception is an HTML page with its own page script (`index.html / index.js`,
  `details.html / details.js`). Every other script the page loads (for example
  `charts.js`) gets its own lifeline.
- Aim for about seven lifelines. When one lifeline per class makes it more, you may go up
  to about ten. Leave out pure plumbing that only passes a call on (a connection helper,
  a logger) and say in the caption what was left out. Above ten, split the action into
  two figures in order instead of merging lifelines.
- A call that only happens under a condition in the code goes in an `opt [condition]`
  group. Parallel calls (`Promise.all`, `Task.WhenAll`) go in a `par [...]` group.

Colours: actors `#dae8fc`/`#6c8ebf`, black text; messages black; groups `#f5f5f5`/`#666666`.

```d2
title: "[Sequence] Webshop - placing an order" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
classes: {
  actor: {style: {fill: "#dae8fc"; stroke: "#6c8ebf"; font-color: "#000000"}}
  call: {style: {stroke: "#000000"}}; reply: {style: {stroke: "#000000"; stroke-dash: 3}}
  group: {style: {fill: "#f5f5f5"; stroke: "#666666"; font-color: "#000000"}}
}
shape: sequence_diagram
customer: Customer {shape: person; class: actor}
web: Web app {class: actor}
api: API {class: actor}
db: Database {shape: cylinder; class: actor}
customer -> web: submits the order form {class: call}
web -> api: POST /orders {class: call}
invalid: "alt [body invalid]" {
  class: group
  api -> web: 400 Bad Request {class: reply}
}
api -> db: INSERT order {class: call}
db -> api: order id {class: reply}
api -> web: 201 Created {class: reply}
web -> customer: shows the confirmation {class: reply}
```

## State machine (UML)

Rules: one filled circle as the initial state and a bullseye for each final state;
states as rounded boxes named after the code's values; every transition labelled
`event [guard] / action` (leave out the parts that do not exist); only transitions the
code allows. Business lifecycle states make it functional too.

```d2
title: "[State machine] Order" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
classes: {
  state: {style: {border-radius: 12}}
}
start: "" {shape: circle; width: 20; style: {fill: black; stroke: "#9ca3af"}}
end: "" {shape: circle; width: 20; style: {fill: black; stroke: "#9ca3af"; double-border: true}}
draft: Draft {class: state}
paid: Paid {class: state}
shipped: Shipped {class: state}
cancelled: Cancelled {class: state}
start -> draft: "create()"
draft -> paid: "pay() [amount ok] / receipt"
draft -> cancelled: "cancel()"
paid -> shipped: "ship() / notify customer"
shipped -> end
cancelled -> end
```

## ER diagram (crow's foot)

Rules: one `sql_table` per table with its key columns (primary key, foreign keys,
unique, the columns the scope uses; leave out audit columns); an arrow for every real
foreign key, from the referencing column to the referenced one, labelled with a verb;
**both ends** show cardinality with crow's foot arrowheads (`cf-one`,
`cf-one-required`, `cf-many`, `cf-many-required`).

```d2
title: "[ER] Webshop - orders" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: right
customer: {
  shape: sql_table
  id: int {constraint: primary_key}
  email: text {constraint: unique}
}
order: {
  shape: sql_table
  id: int {constraint: primary_key}
  customer_id: int {constraint: foreign_key}
  status: text
}
order.customer_id <-> customer.id: "placed by" {
  source-arrowhead.shape: cf-many
  target-arrowhead.shape: cf-one-required
}
```

## Class diagram and domain model (UML)

Rules: only the classes and members that tell the story, never getters or setters;
visibility `+` public, `-` private, `#` protected; **inheritance or realisation** =
hollow triangle at the parent, **composition** = filled diamond at the whole,
**dependency** = dashed arrow; interfaces carry `«interface»` in their name;
multiplicities (`1`, `0..1`, `*`, `1..*`) on associations. A **domain model** is the
conceptual version for the functional side: business concepts with a few attributes,
no methods, no types, multiplicities kept.

Draw a class as an `|md` rectangle, not `shape: class` (D2 colours its body with the
stroke and puts white text on it; `render` warns): the name bold, one member per line
with `+`/`-`/`#` and a `\` line break, `<`/`>` as `&lt;`/`&gt;` ("malformed Markdown").


```d2
title: "[Class] Diagram backends" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
classes: {uml: {shape: rectangle; style: {fill: "#dae8fc"; stroke: "#6c8ebf"; font-color: "#000000"}}}
backend: |md
  **«interface» DiagramBackend**\
  +render_context(diagram): str
| {class: uml}
mermaid: |md
  **MermaidBackend**\
  +render_context(diagram): str
| {class: uml}
diagram: |md
  **Diagram**\
  +title: str\
  +nodes: tuple&lt;Node&gt;
| {class: uml}
node: |md
  **Node**\
  +alias: str
| {class: uml}
mermaid -> backend: realises {target-arrowhead: {shape: triangle; style.filled: false}; style.stroke-dash: 3}
node -> diagram: "1..*" {target-arrowhead: {shape: diamond; style.filled: true}}
backend -> diagram: formats {style.stroke-dash: 3}
```

## Package diagram

Rules: `shape: package` per package or module of the project itself (no third-party
libraries); an arrow means "imports / depends on"; highlight a violated layering rule in
red and say which rule in the caption. Group the packages by the private modules of
`kingmadoc explain facts` (the dominator tree): what only one package leads to belongs
inside it.

```d2
title: "[Package] kingmadoc" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
cli: cli {shape: package}
plan: plan {shape: package}
diagrams: diagrams {shape: package}
documents: documents {shape: package}
cli -> plan: imports
cli -> documents: imports
plan -> diagrams: imports
```

## Activity diagram with swimlanes (UML / BPMN style)

Rules: one lane per role or system, in the order they first act; a filled circle to
start and a bullseye to end; actions as rounded boxes starting with a verb; decisions
as diamonds whose outgoing arrows are labelled (`yes` / `no`, or the condition); hand-
offs cross lanes. For a single role without hand-offs, use a flowchart (same rules, no
lanes). A **user journey** is a flowchart of the screens and choices a user goes
through.

```d2
title: "[Activity] Contact form - handling a message" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
visitor: Visitor {
  start: "" {shape: circle; width: 20; style: {fill: black; stroke: "#9ca3af"}}
  send: Fill in and send the form {style.border-radius: 12}
}
api: API {
  check: Valid and not a bot? {shape: diamond}
  store: Store the message {style.border-radius: 12}
  reject: Return an error {style.border-radius: 12}
}
owner: Site owner {
  read: Read it in Discord {style.border-radius: 12}
  end: "" {shape: circle; width: 20; style: {fill: black; stroke: "#9ca3af"; double-border: true}}
}
visitor.start -> visitor.send -> api.check
api.check -> api.store: "yes"
api.check -> api.reject: "no"
api.reject -> visitor.send
api.store -> owner.read -> owner.end
```

## Use case diagram (UML)

Rules: actors (people or external systems) outside the system boundary; one oval per
user goal inside it, named verb + object; plain lines without arrowheads between an
actor and its use cases; no «include» or «extend» unless the code has that structure.
Pair it with a table of who may do what (routes and permissions).

```d2
title: "[Use case] Webshop" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: right
customer: Customer {shape: person}
admin: Administrator {shape: person}
shop: Webshop {
  order: Place an order {shape: oval}
  track: Track an order {shape: oval}
  stock: Manage the stock {shape: oval}
}
customer -- shop.order
customer -- shop.track
admin -- shop.stock
```

## Data flow diagram with trust boundaries

Rules: the notation of the Microsoft Threat Modeling Tool: External Interactors as
rectangles (a human user as a person), Processes as circles, Data Stores as
`stored_data`; every flow a one-way arrow labelled with **what data** moves and its type
(`[HTTPS]`, `[Binary]`); trust boundaries as dashed red, unfilled boxes named like
the tool's (`Internet Boundary`, `Machine Trust Boundary`). This explains where
sensitive data goes. The threat model ([threat-model.md](threat-model.md)) builds on it
with the tool's STRIDE threats per interaction and the measures the code takes.

```d2
title: "[Data flow] Login" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: right
vars: {
  d2-legend: {
    e: External Interactor
    p: Process {shape: circle}
    s: Data Store {shape: stored_data}
    t: Trust Border Boundary {style: {stroke: red; stroke-dash: 4; fill: transparent}}
  }
}
browser: Browser
internet: "Internet Boundary" {
  style: {stroke: red; stroke-dash: 4; fill: transparent}
  login: "Login API" {shape: circle}
  users: "Users" {shape: stored_data}
}
browser -> internet.login: "e-mail and password [HTTPS]"
internet.login -> internet.users: "password hash lookup [Binary]"
internet.login -> browser: "session cookie [HTTPS]"
```

## Event flow (event storming colours)

Rules: time runs left to right; command (blue, imperative) → aggregate or actor
(yellow) → domain event (orange, past tense) → policy (lilac, "whenever …, …") → next
command; external systems pink. A legend with the colours is required.

```d2
title: "[Event flow] Placing an order" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: right
vars: {
  d2-legend: {
    c: Command {style: {fill: "#a7c7e7"; font-color: "#1f2937"}}
    a: Aggregate {style: {fill: "#fff59d"; font-color: "#1f2937"}}
    e: Domain event {style: {fill: "#ffb74d"; font-color: "#1f2937"}}
    p: Policy {style: {fill: "#ce93d8"; font-color: "#1f2937"}}
  }
}
place: Place order {style: {fill: "#a7c7e7"; font-color: "#1f2937"}}
order: Order {style: {fill: "#fff59d"; font-color: "#1f2937"}}
placed: Order placed {style: {fill: "#ffb74d"; font-color: "#1f2937"}}
reserve: "Whenever an order is placed, reserve the stock" {style: {fill: "#ce93d8"; font-color: "#1f2937"}}
place -> order -> placed -> reserve
```

## Context map (DDD)

Rules: one box per bounded context (a module or service with its own model); each
arrow points from upstream to downstream and is labelled with the integration pattern:
`U` / `D` plus OHS (open host service), PL (published language), ACL (anti-corruption
layer), CF (conformist), SK (shared kernel), or Partnership. Explain the abbreviations in
the table below the figure.

```d2
title: "[Context map] Webshop" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: right
catalog: Catalog context
sales: Sales context
payments: Payment provider (external)
catalog -> sales: "U:OHS/PL D:CF"
payments -> sales: "U:OHS D:ACL"
```

## Algorithm (flowchart, trace table, formula)

Rules: explain what it computes before how. A flowchart of the steps with decisions as
diamonds and every exit labelled (`yes`/`no`, or the condition); at most 15 lines of
pseudocode (`text` block) in the code's names; the formula it evaluates as a display
formula (`$$ … $$`, rendered by GitHub and VS Code); the invariant that holds after
every step, in one sentence; time and space in O-notation, saying what *n* is; and a
trace table on a small input, one row per step, one column per variable. Numbers in
the trace come from running or reading the code, never from memory.

```d2
title: "[Algorithm] Shortest route (Dijkstra)" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
start: "dist[start] = 0, all others ∞; queue = {start}" {shape: rectangle}
empty: "queue empty?" {shape: diamond}
pick: "take the node u with the smallest dist" {shape: rectangle}
goal: "u is the goal?" {shape: diamond}
relax: "for each neighbour v: dist[v] = min(dist[v], dist[u] + w(u, v))" {shape: rectangle}
found: "route found: follow prev[] back" {shape: oval}
none: "no route" {shape: oval}
start -> empty
empty -> none: "yes"
empty -> pick: "no"
pick -> goal
goal -> found: "yes"
goal -> relax: "no"
relax -> empty
```

```text
dist[start] = 0; queue = {start}
while queue:
    u = pop node with smallest dist
    if u == goal: return path(prev, goal)
    for v, w in neighbours(u):
        if dist[u] + w < dist[v]:
            dist[v] = dist[u] + w; prev[v] = u; push v
return no route
```

$$
d(v) = \min_{(u, v) \in E} \big( d(u) + w(u, v) \big)
$$

**Invariant:** every node taken from the queue has its final, shortest distance.
**Complexity:** O((V + E) log V) time with a binary heap, O(V) space; V nodes, E edges.

Trace for the graph A–B (4), A–C (1), C–B (2), from A to B:

| Step | Taken (u) | dist A | dist B | dist C | Queue   |
| ---- | --------- | ------ | ------ | ------ | ------- |
| 0    | –         | 0      | ∞      | ∞      | A       |
| 1    | A         | 0      | 4      | 1      | C, B    |
| 2    | C         | 0      | 3      | 1      | B       |
| 3    | B (goal)  | 0      | 3      | 1      | –       |

## Review checklist

Check every figure against its model's rules above before handing over:

- [ ] It has a title with the model and scope, and a legend when colours, line styles
      or shapes mean something.
- [ ] Sequence: calls solid, replies dashed, groups named `alt/opt/loop [condition]`.
- [ ] Sequence: one class, file or system per lifeline; only a page with its own script
      (`index.html / index.js`) shares one; no `A / B` lifelines.
- [ ] State machine: one initial state, final states, transitions as
      `event [guard] / action`, only transitions the code allows.
- [ ] ER: real foreign keys only, cardinality at both ends, key columns only.
- [ ] Class: hollow triangle for inheritance, filled diamond for composition, dashed for
      dependency; no getters or setters.
- [ ] Activity: lanes per role, labelled decision exits, start and end.
- [ ] Data flow: every flow says what data; trust boundaries dashed red.
- [ ] Algorithm: labelled decision exits, formula, invariant, complexity with *n*
      defined, and a trace table whose numbers come from the code.
- [ ] Names match the code; nothing drawn that the code does not have.
