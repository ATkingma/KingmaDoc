# KingmaDoc

Feature documentation for AI coding agents. KingmaDoc prevents _code blindness_ — the
state where an agent has built something, but you no longer understand what was built
or how to validate it.

- **`plan`** (before implementation): analyzes the codebase, asks up to 5 clarifying
  questions, and writes a Feature Design Doc with Mermaid C4 diagrams.
- **`verify`** (after implementation): compares the design doc against the code and
  reports deviations, risks, and build/test/lint results. _Not implemented yet (phase 2)._

> Status: phase 1 (MVP). Generates C4 Context and Container diagrams; component,
> sequence, and class diagrams are placeholders.

## Install

Requires Python 3.11+.

```bash
git clone <repo-url> kingmadoc && cd kingmadoc
pip install -e ".[dev]"
```

## Usage

```bash
kingmadoc init                       # write a default .featuredoc.yml
kingmadoc plan "Password reset"      # analyze, ask questions, write the design doc
kingmadoc plan "Password reset" -d "Email-based reset flow" --no-input --stdout
kingmadoc verify docs/features/password-reset/design.md   # phase 2
```

By default, docs are written to `docs/features/<feature-slug>/design.md`. See
[`examples/verify-mode-design.md`](examples/verify-mode-design.md) for sample output.

## Configuration

`.featuredoc.yml` in the project root (all keys optional):

```yaml
output_dir: docs/features
template: plan_default.md.j2 # bundled name, or a path relative to the project root
max_questions: 5 # 0-5
project:
  name: null # defaults to the directory name
  description: ""
analyzer:
  max_files: 2000
  tree_depth: 3
  exclude_dirs: [".git", ".venv", "node_modules", "..."]
diagrams: [c4_context, c4_container]
```

Unknown keys are rejected so typos don't go unnoticed.

## Development

```bash
pytest                                   # all tests
pytest tests/test_config.py::test_unknown_key_raises   # one test
```

## License

MIT — see [LICENSE](LICENSE).
