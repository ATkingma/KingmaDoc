# The C4 model (Simon Brown)

Contents: Abstractions · The seven diagrams · Notation rules · Drawing C4 in D2 ·
Palette: draw.io · Mistakes to avoid · Review checklist.

Every C4 figure in an explainer follows this file. It sums up the C4 model as defined
by its creator at [c4model.com](https://c4model.com): the abstractions, the seven
diagram types, the notation rules and the review checklist. C4 shows static structure,
deployment and runtime; for data, state, processes or domain models add the models in
[models.md](models.md).

## Abstractions

"A software system is made up of one or more containers (applications and data stores),
each of which contains one or more components, which in turn are implemented by one or
more code elements." People use software systems.

| Abstraction     | What it is                                                                                   | Is not                                                            |
| --------------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Person          | A human user: actor, role, persona.                                                          | A system account (that is a software system).                     |
| Software system | Delivers value to its users; what one team builds, owns and can see inside (often one repo). | A product domain, bounded context, business capability or team.   |
| Container       | An application or data store that must run for the system to work: a runtime boundary.       | A Docker container per se; a JAR, DLL, module, package or folder. |
| Component       | Related functionality behind a well-defined interface, inside one container (same process).  | Separately deployable; a namespace or folder by itself.           |
| Code element    | A class, interface, enum, function, object or database table that implements a component.    | Worth drawing for every component.                                |

Containers, precisely:

- **Are containers:** a server-side web app, a single-page app in the browser (a second
  container next to its server), a desktop or mobile app, a console app or batch job, a
  serverless function, a database schema, a blob store or bucket, a file system, a
  shell script, **each** queue or topic.
- Cloud storage you own (S3 bucket, RDS database, CDN) is a container, not an external
  system. A message bus is not one container: draw its queues or topics, or label the
  relationship "… via <queue>".
- Deployment is separate: three apps on one server are still three containers.
- Microservices owned by the same team are containers (an API plus its database); a
  service owned by another team is an external software system.

Components, precisely: a controller, or a service or repository interface plus its
implementation classes, is one component. Leave out plain data classes and utilities.
Components map to real groupings in the code, so point to their `path`.

Keep one level of abstraction per diagram. Do not invent levels ("subsystem", "layer",
"subcomponent"), and never show the inside of an external system.

## The seven diagrams

C4 has four core diagrams (levels 1 to 4) and three supporting ones. "You don't need to
use all 4 levels of diagram; only those that add value."

| Diagram           | Scope                              | Shows                                                                                | In an explainer                                          |
| ----------------- | ---------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| 1. System Context | one software system                | the system as one box, its people and the systems it talks to; no technology details | always                                                   |
| 2. Container      | one software system                | its containers, their technology and how they talk; people and systems around them   | always                                                   |
| 3. Component      | one container                      | its components, their responsibility and technology; what they connect to            | for each container worth opening                         |
| 4. Code           | one component                      | the classes, interfaces or tables that implement it (UML class or ER, models.md)     | only for the most important or complex component         |
| System Landscape  | an organisation or several systems | people and software systems, no single focus                                         | project scope with several systems in one repo or org    |
| Dynamic           | one feature, story or use case     | elements (systems, containers or components) with numbered interactions              | a flow that is hard to read from the static diagrams     |
| Deployment        | one environment (e.g. production)  | deployment nodes (hosts, VMs, Docker, PaaS) with the container instances they run    | whenever the code has Dockerfiles, compose, IaC or CI/CD |

A sequence diagram (models.md) is an accepted way to draw a dynamic diagram. Container
diagrams leave out load balancers, replicas and failover: that is the deployment
diagram's job, one per environment.

## Notation rules

Each diagram "can stand alone, and be (mostly) understood without a narrative".

- **Title** with the diagram type and scope: `[System Context] Webshop`,
  `[Container] Webshop`, `[Component] Webshop - API`, `[Deployment] Webshop - production`,
  `[Dynamic] Webshop - placing an order`.
- **Legend** explaining every shape, colour and line style used (`d2-legend`).
- **Every element:** a name, its type and its technology (containers, components and
  deployment nodes), in this layout, with no description line: the short description of
  its responsibility goes into the table under the figure.

  ```text
  **Name**
  [Container: ASP.NET Core 10]
  ```

- **Fixed width:** every element class gets `width: 250` (250-260), so D2 does not cut
  the text.

- **Every relationship:** one direction (no two-headed arrows), a label that states the
  intent and reads in the arrow's direction ("Sends order e-mails using", not "Uses" or
  "e-mail"), and between containers the technology or protocol: `[HTTPS/JSON]`,
  `[SQL]`, `[AMQP]`. Several interactions between the same two elements become one
  arrow with an inclusive label ("Places orders using"); the individual
  steps go in a dynamic diagram.
- **Boundaries** as a dashed box named after the system or container they enclose. No
  `grid-rows`/`grid-columns` inside a boundary: ELK then draws the arrows as straight
  lines through the blocks.
- **Nested deployment nodes:** one arrow to the outer node, not one to each child.
- **Colours** consistent across all figures: the palette below. Explain acronyms in the
  legend or the table under the figure.
- At most about fifteen elements per diagram; split larger ones by area or feature at
  the same level of abstraction.

## Drawing C4 in D2

Paste this `classes` block at the top of every C4 figure (only the classes it uses),
label elements with Markdown (`|md … |`) and add a `d2-legend` for the classes used.

```d2
classes: {
  person: {shape: c4-person; style: {fill: "#08427b"; stroke: "#073b6f"; font-color: "#ffffff"}; width: 250}
  system: {shape: rectangle; style: {fill: "#1168bd"; stroke: "#0b4884"; font-color: "#ffffff"}; width: 250}
  external: {shape: rectangle; style: {fill: "#999999"; stroke: "#6b6b6b"; font-color: "#ffffff"}; width: 250}
  container: {shape: rectangle; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  database: {shape: cylinder; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  component: {shape: rectangle; style: {fill: "#85bbf0"; stroke: "#5d82a8"; font-color: "#000000"}; width: 250}
  boundary: {label.near: top-left; style: {fill: transparent; stroke: "#888888"; stroke-dash: 4; font-size: 15}}
  node: {label.near: top-left; style: {fill: transparent; stroke: "#888888"; font-size: 15}}
}
title: "[System Context] Webshop" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
vars: {
  d2-legend: {
    p: Person {class: person}
    s: Software system {class: system}
    x: External software system {class: external}
    a: "" {style.opacity: 0}
    b: "" {style.opacity: 0}
    a -> b: Relationship
  }
}
customer: |md
  **Customer**\
  [Person]
| {class: person}
shop: |md
  **Webshop**\
  [Software System]
| {class: system}
mail: |md
  **E-mail service**\
  [Software System]
| {class: external}
customer -> shop: "Places orders using"
shop -> mail: "Sends order e-mails using"
```

**Container** (level 2): the system becomes a dashed boundary with its containers;
relationships name the protocol.

```d2
classes: {
  person: {shape: c4-person; style: {fill: "#08427b"; stroke: "#073b6f"; font-color: "#ffffff"}; width: 250}
  external: {shape: rectangle; style: {fill: "#999999"; stroke: "#6b6b6b"; font-color: "#ffffff"}; width: 250}
  container: {shape: rectangle; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  database: {shape: cylinder; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  boundary: {label.near: top-left; style: {fill: transparent; stroke: "#888888"; stroke-dash: 4; font-size: 15}}
}
title: "[Container] Webshop" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
vars: {
  d2-legend: {
    p: Person {class: person}
    c: Container {class: container}
    d: Container: data store {class: database}
    x: External software system {class: external}
    bd: Software system boundary {class: boundary}
    a: "" {style.opacity: 0}
    b: "" {style.opacity: 0}
    a -> b: Relationship
  }
}
customer: |md
  **Customer**\
  [Person]
| {class: person}
shop: "Webshop [Software System]" {
  class: boundary
  web: |md
    **Web app**\
    [Container: Next.js 15]
  | {class: container}
  api: |md
    **API**\
    [Container: ASP.NET Core 10]
  | {class: container}
  db: |md
    **Database**\
    [Container: PostgreSQL 16]
  | {class: database}
}
mail: |md
  **E-mail service**\
  [Software System]
| {class: external}
customer -> shop.web: "Orders using [HTTPS]"
shop.web -> shop.api: "Places orders [HTTPS/JSON]"
shop.api -> shop.db: "Reads/writes orders [SQL]"
shop.api -> mail: "Sends e-mails using [SMTP]"
```

**Component** (level 3): one container as the boundary; components name the code
construct and point to their path in the table below the figure.

```d2
classes: {
  container: {shape: rectangle; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  database: {shape: cylinder; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  component: {shape: rectangle; style: {fill: "#85bbf0"; stroke: "#5d82a8"; font-color: "#000000"}; width: 250}
  boundary: {label.near: top-left; style: {fill: transparent; stroke: "#888888"; stroke-dash: 4; font-size: 15}}
}
title: "[Component] Webshop - API" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
vars: {
  d2-legend: {
    c: Container {class: container}
    k: Component {class: component}
    d: Container: data store {class: database}
    bd: Container boundary {class: boundary}
    a: "" {style.opacity: 0}
    b: "" {style.opacity: 0}
    a -> b: Relationship
  }
}
web: |md
  **Web app**\
  [Container: Next.js 15]
| {class: container}
api: "API [Container: ASP.NET Core 10]" {
  class: boundary
  orders: |md
    **Orders controller**\
    [Component: ASP.NET controller]
  | {class: component}
  store: |md
    **Order repository**\
    [Component: EF Core]
  | {class: component}
}
db: |md
  **Database**\
  [Container: PostgreSQL 16]
| {class: database}
web -> api.orders: "Posts orders [HTTPS/JSON]"
api.orders -> api.store: "Saves the order using"
api.store -> db: "Reads and writes [SQL]"
```

**Deployment**: nested deployment nodes (`[Deployment Node: …]`) with the container
instances they run; infrastructure (proxy, DNS) only when the code configures it.

```d2
classes: {
  container: {shape: rectangle; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  database: {shape: cylinder; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  node: {label.near: top-left; style: {fill: transparent; stroke: "#888888"; font-size: 15}}
}
title: "[Deployment] Webshop - production" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
vars: {
  d2-legend: {
    n: Deployment node {class: node}
    c: Container instance {class: container}
    d: Container instance: data store {class: database}
    a: "" {style.opacity: 0}
    b: "" {style.opacity: 0}
    a -> b: Relationship
  }
}
server: "VPS [Deployment Node: Ubuntu 24.04]" {
  class: node
  docker: "Docker [Deployment Node: Docker Compose]" {
    class: node
    web: "Web app [Container: Next.js 15] :3000" {class: container}
    api: "API [Container: ASP.NET Core 10] :8080" {class: container}
    db: "Database [Container: SQLite file]" {class: database}
  }
}
server.docker.web -> server.docker.api: "Places orders [HTTP]"
server.docker.api -> server.docker.db: "Reads and writes [SQLite]"
```

**Dynamic**: one feature; the labels are numbered in order. (For many steps or
replies, draw a sequence diagram instead; see models.md.)

```d2
classes: {
  person: {shape: c4-person; style: {fill: "#08427b"; stroke: "#073b6f"; font-color: "#ffffff"}; width: 250}
  container: {shape: rectangle; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
  database: {shape: cylinder; style: {fill: "#438dd5"; stroke: "#3c7fc0"; font-color: "#ffffff"}; width: 250}
}
title: "[Dynamic] Webshop - placing an order" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
direction: down
vars: {
  d2-legend: {
    p: Person {class: person}
    c: Container {class: container}
    d: Container: data store {class: database}
    a: "" {style.opacity: 0}
    b: "" {style.opacity: 0}
    a -> b: Interaction, in numbered order
  }
}
customer: "Customer [Person]" {class: person}
web: "Web app [Container: Next.js 15]" {class: container}
api: "API [Container: ASP.NET Core 10]" {class: container}
db: "Database [Container: PostgreSQL 16]" {class: database}
customer -> web: "1. Submits order form"
web -> api: "2. Posts order [HTTPS/JSON]"
api -> db: "3. Saves order [SQL]"
```

A **System Landscape** is drawn like the context diagram, without a system in focus.

## Palette: draw.io

With `explain: {palette: drawio}` in `.featuredoc.yml` (for readers in light mode only;
render with `kingmadoc render --light`), use these colours instead of the C4 blues. One
text colour (black) for every C4 figure.

| Element                              | Fill      | Stroke    | Text      |
| ------------------------------------ | --------- | --------- | --------- |
| Person, system, container, component | `#dae8fc` | `#6c8ebf` | `#000000` |
| External system                      | `#999999` | `#6b6b6b` | `#000000` |
| Group, frame, boundary               | `#f5f5f5` | `#666666` | `#000000` |
| Arrow                                | —         | `#000000` | `#000000` |

Status (traffic light), fill / stroke: green `#d5e8d4` / `#82b366`, red `#f8cecc` /
`#b85450`, orange `#ffe6cc` / `#d79b00`, grey `#f5f5f5` / `#666666`.

```text
classes: {
  person: {shape: c4-person; style: {fill: "#dae8fc"; stroke: "#6c8ebf"; font-color: "#000000"}; width: 250}
  container: {shape: rectangle; style: {fill: "#dae8fc"; stroke: "#6c8ebf"; font-color: "#000000"}; width: 250}
  external: {shape: rectangle; style: {fill: "#999999"; stroke: "#6b6b6b"; font-color: "#000000"}; width: 250}
  boundary: {label.near: top-left; style: {fill: "#f5f5f5"; stroke: "#666666"; stroke-dash: 4; font-color: "#000000"; font-size: 15}}
}
(* -> *)[*].style.stroke: "#000000"
```

## Mistakes to avoid

- A description line inside a block (it goes into the table), or blocks without a
  fixed `width` (D2 cuts the text).

- A message bus, API gateway or service mesh as one box in the middle: draw the queues
  or topics, or label the relationship "… via <queue>".
- JARs, packages, namespaces or folders as containers; cloud storage you own as an
  external system; shared libraries as containers (they are components where used).
- Unlabelled arrows, "Uses", two-headed arrows, labels that contradict the arrow.
- Missing element types or technology, unexplained colours or acronyms, no title.
- One giant diagram, or mixed levels (a class next to a container).
- Decisions drawn into diagrams: they belong in the decisions table (or ADRs).

## Review checklist

Before handing over, check every C4 figure; fix it until every answer is yes.

- [ ] It has a title with the diagram type and scope, and a legend.
- [ ] Every element has a name, a type and (containers, components) a technology; its
      description is in the table under the figure.
- [ ] Every acronym, colour, shape and line style is explained (legend or table).
- [ ] Every arrow has one direction and a specific label that matches it; arrows
      between containers name the protocol.
- [ ] One level of abstraction; nothing inside external systems; at most about
      fifteen elements.
