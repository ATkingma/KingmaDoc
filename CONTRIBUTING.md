# Contributing to KingmaDoc

Thanks for helping! Please open an issue before large changes, so we can agree on the
approach first. Coding and documentation rules are in
[`docs/conventions.md`](docs/conventions.md) (start with the rule summary table).

## Dev setup

Requires Python 3.11+.

```bash
git clone https://github.com/ATkingma/KingmaDoc && cd KingmaDoc
python -m venv .venv
.venv/bin/pip install -e ".[dev]"        # Windows: .venv\Scripts\pip install -e ".[dev]"
.venv/bin/kingmadoc --help
```

With [uv](https://docs.astral.sh/uv/): `uv venv -p 3.11 .venv && uv pip install -p .venv -e '.[dev]'`.

Templates live in `src/kingmadoc/templates/` and are shipped inside the package,
so edits are picked up immediately in an editable install.

## Running the tests

```bash
.venv/bin/pytest                                             # everything
.venv/bin/pytest tests/test_config.py                        # one file
.venv/bin/pytest tests/test_config.py::test_unknown_key_raises   # one test
python3 .claude/skills/checking-conventions/scripts/check_conventions.py   # convention checks
```

- **Snapshots.** Diagram output is compared with files in `tests/fixtures/`. After an
  intended output change, regenerate the backend snapshots and review the diff:
  `KINGMADOC_UPDATE_SNAPSHOTS=1 .venv/bin/pytest tests/test_diagram_backends.py`.
- **Real renderers (optional).** `tests/test_diagram_backends.py` also compiles the
  PlantUML and D2 output when the tools are available: put `d2` on `PATH` (or set
  `D2_BIN`) and `plantuml` on `PATH` (or set `PLANTUML_JAR`, needs Java). Otherwise these
  tests are skipped.
- **Agent skill.** `skill/cursor.md`, `codex.md` and `copilot.md` are generated from
  `skill/SKILL.md`. After changing `SKILL.md`, run `python3 scripts/build_skill_variants.py`;
  `tests/test_skill.py` fails on stale variants, and also when the skill's output format
  no longer matches the templates.
- **Examples.** After changing a template or the generator, regenerate
  `examples/verify-mode-plan.md` (see `CLAUDE.md` for the command).

CI runs the test suite on Python 3.11–3.13 on Linux, macOS and Windows.

## Adding a diagram backend

A backend turns the backend-neutral diagram model into one diagram language. Look at
`src/kingmadoc/diagrams/d2.py` for a compact example.

1. **Create `src/kingmadoc/diagrams/<name>.py`.** It is a plain module (no class) that
   satisfies the `DiagramBackend` protocol in `diagrams/base.py`: a `LABEL` constant
   (shown in headings, e.g. `"D2"`) and the five functions `render_context`,
   `render_container`, `render_component`, `render_sequence` and `render_class`, with the
   same signatures as in `mermaid.py`.
2. **Reuse the shared model.** Call `base.build_context()` (and the other `build_*`
   functions) and only format the returned `Diagram`. Validation, unique aliases and
   relationship lookup already happen there, so all backends behave the same.
3. **Escape for your language.** Every label must survive quotes, backslashes, `$`, `;`
   and `#`, and must stay on one line. Return one fenced block via `base.fence()`.
4. **Register it** in `BACKENDS` in `src/kingmadoc/diagrams/__init__.py` and in
   `DIAGRAM_FORMATS` in `src/kingmadoc/config.py` (a test checks they match).
5. **Placeholder diagrams.** `src/kingmadoc/templates/functional_design.md.j2` and
   `technical_design.md.j2` contain a flowchart and an ER diagram per format; add a
   `{% elif diagram_format == "<name>" %}` branch to each.
6. **Tests.** Add the file extension to `EXTENSIONS` in
   `tests/test_diagram_backends.py`, generate the snapshots (see above) and check them
   with the real renderer. If the tool can be scripted, add a `*_compiles` test like
   the D2 one.
7. **Docs.** Mention the format in `README.md` (configuration table), `CLAUDE.md`, and
   `kingmadoc init`'s comment in `config.default_config_yaml()`.

## Adding a template

**Changing a bundled template** (`src/kingmadoc/templates/*.md.j2`): Jinja2 runs sandboxed
(`SandboxedEnvironment`) with `StrictUndefined`, so you can only use variables that are passed in:

- `plan_default.md.j2`, `functional_design.md.j2`, `technical_design.md.j2`: every field
  of `PlanContext` (`src/kingmadoc/plan/generator.py`); the extra designs also get
  `plan_file` and `data_stores`.
- `adr.md.j2`: `number`, `title`, `status`, `statuses`, `date`.

Keep the headings of the plan template in sync with the "Output format" section of
`skill/SKILL.md`; `tests/test_skill.py` compares them.

**Using a custom plan template in a project** needs no code: set `template:` in
`.featuredoc.yml` to an explicit path such as `./docs/my_plan.md.j2` (relative to the
project root). KingmaDoc never picks up templates from the project root on its own, and
every template runs in Jinja's sandbox, so custom templates cannot call into Python.

**Adding a new optional document** (like the functional design):

1. Add a field to `ExtraDesignsConfig` in `src/kingmadoc/config.py`, whose default names
   the bundled template (parsing is generic), and add it to the `extra_designs:` block in
   `default_config_yaml()`.
2. Add an `ExtraDesign(name, suffix)` entry to `EXTRA_DESIGNS` in
   `src/kingmadoc/plan/generator.py`; `plan` then writes it next to the plan doc when
   it is enabled. Importing the generator fails if the two lists don't match.
3. Create the template in `src/kingmadoc/templates/`.
4. Add tests (see `tests/test_functional_design.py`), a format block to
   `skill/SKILL.md` (and rebuild the variants), and a row in the README's configuration
   table.

## Pull requests

- Keep changes focused, with tests. `pytest` and the convention checker must pass.
- Every new Markdown file must be linked from `docs/index.md`.
- Add a line to the `Unreleased` section of [CHANGELOG.md](CHANGELOG.md).
- By contributing, you agree that your contribution is licensed under the MIT License.
