# Feature: Add a verify mode that compares a plan doc against the implemented code.

| | |
|---|---|
| **Project** | KingmaDoc |
| **Status** | Draft |
| **Generated** | 2026-09-26T19:26+02:00 by KingmaDoc 0.1.1 |

> Generated before implementation. Fill in every _TODO_ and review everything marked
> _(inferred)_: it comes from the codebase analysis and is a starting point, not the truth.

## One-sentence summary

Add a verify mode that compares a plan doc against the implemented code.

**Full description:** Add a verify mode that compares a plan doc against the implemented code. It reports deviations and test/lint results.

## Scope (in / out)

**In scope**

- _TODO: what this feature delivers._

**Out of scope**

- _TODO: what it deliberately does not do._

## Assumptions

- _(inferred)_ Built on the existing stack: Click, Jinja2, Python.
- _TODO: what must be true for this plan to work (users, data, services, limits)._

## Risks

- _TODO: what could go wrong, and how you will notice or limit it._

## C4 Context (Mermaid)

Who uses the system and which external systems it depends on.

```mermaid
C4Context
    title System Context: KingmaDoc

    Person(user, "User", "Person who uses the feature")
    System(kingmadoc, "KingmaDoc")

    Rel(user, kingmadoc, "Uses")
```

## C4 Container (Mermaid)

The runnable units inside the system _(inferred from source directories)_.

```mermaid
C4Container
    title Containers: KingmaDoc

    Person(user, "User", "Person who uses the feature")
    System_Boundary(kingmadoc_boundary, "KingmaDoc") {
        Container(kingmadoc, "kingmadoc", "Python", "Source module src/kingmadoc/")
    }

    Rel(user, kingmadoc, "Uses")
```

## Open questions

- [ ] _TODO: anything else that must be decided before implementation._

**Answered while planning**

- **What problem does this feature solve, and for whom?** Developers lose track of what an AI agent built; they need a verification doc.
- **Who or what triggers it (end user, scheduled job, external system, ...)?** The developer, via the kingmadoc verify command.
- **Which external systems, services, or data stores does it interact with?** None; reads local files and runs the project test command.
- **Which existing modules will change? (detected modules: `src/kingmadoc`)** src/kingmadoc/cli.py and a new src/kingmadoc/verify package.
- **How will you know it works? List the acceptance criteria.** verify produces a doc listing deviations from the plan doc and test/lint results.

## Appendix: codebase context _(inferred)_

- **Tech stack:** Click, Jinja2, Python
- **Entry points:** _none found_
- **Config files:** `pyproject.toml`
- **Test directories:** `tests`

| Language | Files |
|---|---|
| python | 45 |
| markdown | 14 |
| jinja | 4 |
| yaml | 2 |
| json | 1 |
| toml | 1 |

<details>
<summary>File tree (87 files)</summary>

```text
KingmaDoc/
├── .claude/
│   ├── skills/
│   │   └── checking-conventions/
│   │       └── …
│   └── settings.json
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── conventions.md
│   └── index.md
├── examples/
│   └── verify-mode-plan.md
├── scripts/
│   └── build_skill_variants.py
├── skill/
│   ├── codex.md
│   ├── copilot.md
│   ├── cursor.md
│   └── SKILL.md
├── src/
│   └── kingmadoc/
│       ├── diagrams/
│       │   └── …
│       ├── plan/
│       │   └── …
│       ├── templates/
│       │   └── …
│       ├── verify/
│       │   └── …
│       ├── __init__.py
│       ├── adr.py
│       ├── cli.py
│       ├── config.py
│       ├── documents.py
│       ├── exceptions.py
│       ├── naming.py
│       └── templating.py
├── tests/
│   ├── fixtures/
│   │   ├── backends/
│   │   │   └── …
│   │   └── mermaid/
│   │       └── …
│   ├── test_adr.py
│   ├── test_analyzer.py
│   ├── test_cli.py
│   ├── test_cli_encoding.py
│   ├── test_cli_init.py
│   ├── test_cli_plan_custom_template.py
│   ├── test_cli_sigint.py
│   ├── test_cli_verify_config.py
│   ├── test_config.py
│   ├── test_config_poetry.py
│   ├── test_config_shape.py
│   ├── test_diagram_backends.py
│   ├── test_diagrams_mermaid.py
│   ├── test_documents.py
│   ├── test_extra_designs_coverage.py
│   ├── test_functional_design.py
│   ├── test_generator.py
│   ├── test_manifests.py
│   ├── test_output_dir.py
│   ├── test_plan_e2e.py
│   ├── test_skill.py
│   ├── test_summary_slug_diagram_defaults.py
│   ├── test_technical_design.py
│   ├── test_templating_security.py
│   └── test_verify_stub.py
├── .featuredoc.yml
├── .gitignore
├── CHANGELOG.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
└── README.md
```

</details>
