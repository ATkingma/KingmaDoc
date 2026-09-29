# User stories, use cases, screens and evil user stories

Contents: Rules per part · Screens: wireframe first, screenshots when allowed.

The functional red thread, for the models `user_stories`, `use_case`, `screens` and
`evil_user_stories`. Where it goes: `functional.md` sections 4 to 6 in an FO/TO
([split.md](split.md)), arc42 section 4 (Business context) or the c4 format's "How it
works" in a single document. `kingmadoc explain scaffold` writes the empty tables; the
format is the `functional.md` block in [split.md](split.md).

## Rules per part

- **User stories:** one per use case in the use case diagram: what an actor can do in
  the code (a page, a form, a command, an API an outside system calls). "So that" only when the
  code, docs or history state the reason; otherwise `—`. For a branch, only the stories
  the branch adds or changes, marked _(new)_ or _(changed)_.
- **Use case:** the main scenario follows the code path; every exception is a check
  the code makes, with the message it shows.
- **Screen:** see [Screens](#screens-wireframe-first-screenshots-when-allowed) below. A story
  without a screen of its own (an API, a job) says so in one line instead.
- **Evil user stories:** two to four per story, how that story's input, IDs, rights or
  volume could be misused (e.g. change another user's ID in the URL, send a script as a
  name, send the form 1,000 times). The mitigation is the `SM-n` of `technical.md`
  that stops it, or _Nothing in the code stops this._ as a plain fact; never a proposal.

## Screens: wireframe first, screenshots when allowed

A screen shows what the user really sees. The explainer never waits for it: draw the
wireframes (step 4) first, so the document is finished and rendered in one go. Real
screenshots replace them when you may use the app:

1. **May you?** Only when the request says so ("start the app", "it runs at
   http://localhost:5000"). Otherwise offer it at hand-over (SKILL.md Step 6) and, on
   yes, do steps 2 and 3 and render again. Never ask before the document exists.
2. **Start it** with the project's own command (README, `package.json` scripts,
   `dotnet run`, `docker compose up`) in the background, and wait for its URL. Never
   change code or configuration to make it start, never use production data, and sign
   in only with a test account the user gives you.
3. **Capture** all screens in one go, from the subject's folder:
   `kingmadoc screenshots <url> /contact=screen-us-1 /orders=screen-us-2 -o img`
   (1280×800; one browser with Playwright, else `npx -y playwright screenshot` per
   screen). Without KingmaDoc, use a browser tool your agent has.
   Show the state the use case is about (a form with an error message, a filled list).
   Stop the app afterwards. `kingmadoc render` leaves screenshots as they are.
4. **Wireframe** in D2, always first and whenever the app cannot run here (a desktop or
   mobile app, missing secrets or database, no permission), drawn from the view code: the fields,
   buttons and messages as the template or component names them, top to bottom. Say
   "wireframe" in the title and caption.

**A "design" is a wireframe.** When the user asks for a design ("ontwerp", mock-up),
never use screenshots: draw black-and-white, Balsamiq-style wireframes with
`vars: {d2-config: {sketch: true}}` and black strokes (`stroke: "#000000"`).

Rules: one container per screen named after its route or window; only elements the
view code has, with its texts **literally and in the same order**. Widgets:

| Widget          | Drawn as                                                                     |
| --------------- | ---------------------------------------------------------------------------- |
| Input field     | `Label` above `[ placeholder ]` with the placeholder text grey (`#999999`)   |
| Dropdown        | `[ <default value>  v ]`                                                     |
| Primary button  | fill `#333333`, white text; other buttons unfilled                           |
| Checkbox        | `☐ Label` / `☑ Label`                                                        |
| Tile            | a small box with its title and number                                        |
| Table           | a grid: header row fill `#e6e6e6`, then two or three example rows            |
| Chart           | a circle with a fixed `width` **and** `height` (a placeholder, not data)     |
| Error message   | a dashed red box                                                             |

Grids, or the layout breaks:

- **Always `grid-rows` and `grid-columns` together.** Only `grid-columns` fills column by
  column (a table comes out transposed); only `grid-rows` spreads the cells unevenly.
- A text shape never has an empty label: use `" "` with a transparent style.
- `top` is reserved in D2: never name a shape `top`.
- A wide control panel and a pie next to a table go in separate sub-rows, or the circle
  stretches.

**Check before rendering:** dump every heading, label, button text, placeholder,
dropdown default, hint and table column from the view (HTML, template, JS) and check
that each is in the wireframe literally and in the same order. Name the view file in
the caption in a code span (`` `src/views/contact.html` ``): `kingmadoc explain check`
then warns about every wireframe text the view does not have.

```d2
title: "[Screen] Contact form - wireframe of /contact" {shape: text; near: top-center; style: {font-size: 24; bold: true}}
vars: {d2-config: {sketch: true}}
direction: down
screen: "/contact" {
  grid-rows: 5
  grid-columns: 1
  grid-gap: 12
  style: {fill: transparent; stroke: "#000000"}
  name: "Name *   [ Your name ]" {style: {fill: transparent; stroke: "#000000"}}
  subject: "Subject   [ General question  v ]" {style: {fill: transparent; stroke: "#000000"}}
  message: "Message *   [ Your message ]" {height: 100; style: {fill: transparent; stroke: "#000000"}}
  error: "! Fill in a valid e-mail address" {style: {fill: transparent; stroke: "#dc2626"; stroke-dash: 3}}
  buttons: " " {
    grid-rows: 1
    grid-columns: 2
    grid-gap: 12
    style: {fill: transparent; stroke: transparent}
    cancel: Cancel {style: {fill: transparent; stroke: "#000000"; border-radius: 8}}
    send: Send {style: {fill: "#333333"; stroke: "#000000"; font-color: "#ffffff"; border-radius: 8}}
  }
}
```
