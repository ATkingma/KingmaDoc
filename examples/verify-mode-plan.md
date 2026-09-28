---
kingmadoc: 1
feature: "add-a-verify-mode-that-compares-a-plan"
status: draft
requirements: [REQ-1]
files_expected: ["src/kingmadoc/cli.py", "src/kingmadoc/verify"]
---
# Feature: Add a verify mode that compares a plan doc against the implemented code.

| | |
|---|---|
| **Project** | KingmaDoc |
| **Status** | Draft |
| **Generated** | 2026-09-28T11:26+02:00 by KingmaDoc 0.3.0.dev8 |

> Generated before implementation. Fill in every _TODO_ and review everything marked
> _(inferred)_: it comes from the codebase analysis and is a starting point, not the truth.

## One-sentence summary

Add a verify mode that compares a plan doc against the implemented code.

## Scope (in / out)

**In scope**

- _TODO: what this feature delivers._

**Out of scope**

- _TODO: what it deliberately does not do._

## Requirements

_Rewrite each in EARS: WHEN <trigger> THE SYSTEM SHALL <response>._

- **REQ-1**: verify produces a doc listing deviations from the plan doc and test/lint results

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
| python | 112 |
| markdown | 28 |
| jinja | 6 |
| json | 5 |
| yaml | 3 |
| toml | 1 |

<details>
<summary>File tree (294 files)</summary>

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
│       ├── ci.yml
│       └── release.yml
├── .hypothesis/
│   ├── constants/
│   │   ├── 021ecad571f501c4
│   │   ├── 0379b6ca57f0783f
│   │   ├── 0452f760e23a6d88
│   │   ├── 06192107b861970d
│   │   ├── 06ef3073f3824ec2
│   │   ├── 07876857aeea90b1
│   │   ├── 08cf9a45d6a50050
│   │   ├── 0b0dfdcede5596e1
│   │   ├── 0bad6ccfaf25648b
│   │   ├── 0e97d01973676578
│   │   ├── 0fe522cdbe58de88
│   │   ├── 134ec28059d06de2
│   │   ├── 15f3fb32b16d7e57
│   │   ├── 18f6b8ff2f1baab4
│   │   ├── 1b994a5d0c3430c4
│   │   ├── 2003bed8cb6acdf2
│   │   ├── 2916d5e15f88e018
│   │   ├── 2b68fb57acc40084
│   │   ├── 2b782d5c2f962f88
│   │   ├── 2be0ee3271f47e06
│   │   ├── 2e00d1a2bca2c453
│   │   ├── 30b41cb134ad3951
│   │   ├── 321c789fc8b4c0f3
│   │   ├── 36224745265ee8c1
│   │   ├── 37b48c44fc264edf
│   │   ├── 390efa9697d4e1bf
│   │   ├── 429e7d227d43fa43
│   │   ├── 433c532377bbde84
│   │   ├── 4457a7b799badfdf
│   │   ├── 472a546c691778e1
│   │   ├── 488a16471d4a5a9a
│   │   ├── 4c88cacf6c8e4c7d
│   │   ├── 4d29db71b1bc8b24
│   │   ├── 4f38a2b8fdbc0e4b
│   │   ├── 51a950d876d1ab4e
│   │   ├── 51c35758aac2bab5
│   │   ├── 52fa9b12a8e99f1c
│   │   ├── 55915e632dbf0f71
│   │   ├── 561fe03ae02f5a17
│   │   ├── 56c32eb59a5ec5ed
│   │   ├── 57e843cfe884a224
│   │   ├── 583a89d35ba933dd
│   │   ├── 58d99efc68aa19b7
│   │   ├── 5d45513b79aabad7
│   │   ├── 5f0dcf0398739489
│   │   ├── 5f8c64643045c357
│   │   ├── 60831149ff3a2967
│   │   ├── 686c8cce11251820
│   │   ├── 69eaf0facf3541e7
│   │   ├── 6b0fa85cb45db293
│   │   ├── 6ba6186093f01b85
│   │   ├── 7294e3a783cbf3a8
│   │   ├── 7690150393b314b0
│   │   ├── 7716c173bdc714c6
│   │   ├── 78f4187c208c7544
│   │   ├── 7bfef669ca020280
│   │   ├── 7c1e245a4af2a784
│   │   ├── 7c3cfd7bca628b35
│   │   ├── 7c6945c0632031eb
│   │   ├── 80f3eb9fe296aa5f
│   │   ├── 8310d3b7a356f92f
│   │   ├── 86419387d03b2884
│   │   ├── 87d557d4d7ce8e21
│   │   ├── 8b1b03f5681dbbd2
│   │   ├── 8dbb0f299a88491e
│   │   ├── 8ee2b55b51643314
│   │   ├── 9047d8cfcf2f6c04
│   │   ├── 91e931027e8ebe98
│   │   ├── 95c1bd9692d5af02
│   │   ├── 969910a0ba7bf0a2
│   │   ├── 982f45a072cecbbb
│   │   ├── 9e17c1aadef85e32
│   │   ├── a537bbf4207c137b
│   │   ├── aaad66f0208d6fda
│   │   ├── adb700443bac7ce4
│   │   ├── b14d3b80cc53ed3d
│   │   ├── b4489de5426f1782
│   │   ├── b4ad5a7efa63c99a
│   │   ├── b607a0ae6852e1cc
│   │   ├── b6dad0dd5ebdf5ec
│   │   ├── bacc1063c7332f9d
│   │   ├── bb0b868e4b9a8187
│   │   ├── bbad5588eb7b8055
│   │   ├── bee5e67a8e93cb55
│   │   ├── c06f4747e82bf550
│   │   ├── c0b457a05760d55b
│   │   ├── c12237819ce468fd
│   │   ├── c743dc86980c4608
│   │   ├── c7c62939844fec2e
│   │   ├── cc4dfad2dc9d75e2
│   │   ├── ccd6d148a9b2486f
│   │   ├── d5d6e65cc7402c90
│   │   ├── d6e5d66b09a82b49
│   │   ├── dc8b9fdffcf4ce95
│   │   ├── e36626a891f1bf04
│   │   ├── e69acc629894311a
│   │   ├── ea35e4be0e371411
│   │   ├── eb95a699ef557106
│   │   ├── f1297fd267b34331
│   │   ├── f16726e173deedc4
│   │   ├── f4481751579327cb
│   │   ├── f4a76cd809f6b59b
│   │   ├── fb02557056414592
│   │   ├── fdfd47c59de6a608
│   │   └── fff51a5fcff07aa9
│   ├── examples/
│   │   ├── 04e6b3400353b141/
│   │   │   └── …
│   │   ├── 1fe65f17de776f9b/
│   │   │   └── …
│   │   ├── 69596e946b8b389f/
│   │   │   └── …
│   │   └── a7da011a58f5abe3/
│   │       └── …
│   ├── unicode_data/
│   │   └── 14.0.0/
│   │       └── …
│   └── .gitignore
├── .import_linter_cache/
│   ├── .gitignore
│   ├── 3516dc116b537972f63cac11b7ceb5fffe116986.data.json
│   ├── 7972b21a515604c6ceefaf3a33ef88e57b8115b6.data.json
│   ├── CACHEDIR.TAG
│   └── kingmadoc.meta.json
├── docs/
│   ├── conventions.md
│   ├── index.md
│   ├── releasing.md
│   ├── roadmap.md
│   └── test-plan.md
├── examples/
│   └── verify-mode-plan.md
├── scripts/
│   ├── build_skill_variants.py
│   ├── build_threat_reference.py
│   ├── import_tmt_knowledge_base.py
│   └── run_evals.py
├── skill/
│   ├── explaining-code/
│   │   ├── reference/
│   │   │   └── …
│   │   └── SKILL.md
│   ├── reference/
│   │   ├── diagram-rules.md
│   │   └── formats.md
│   ├── codex.md
│   ├── copilot.md
│   ├── cursor.md
│   └── SKILL.md
├── src/
│   └── kingmadoc/
│       ├── diagrams/
│       │   └── …
│       ├── facts/
│       │   └── …
│       ├── plan/
│       │   └── …
│       ├── templates/
│       │   └── …
│       ├── threats/
│       │   └── …
│       ├── verify/
│       │   └── …
│       ├── __init__.py
│       ├── about.py
│       ├── adr.py
│       ├── cli.py
│       ├── config.py
│       ├── d2_binary.py
│       ├── documents.py
│       ├── exceptions.py
│       ├── explain.py
│       ├── git.py
│       ├── naming.py
│       ├── plandoc.py
│       ├── raster.py
│       ├── render.py
│       ├── scaffold.py
│       ├── screenshots.py
│       ├── skills.py
│       ├── templating.py
│       └── vscode.py
├── tests/
│   ├── data/
│   │   └── d2-sample.svg
│   ├── fixtures/
│   │   ├── backends/
│   │   │   └── …
│   │   └── mermaid/
│   │       └── …
│   ├── conftest.py
│   ├── test_adr.py
│   ├── test_adr_numbering.py
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
│   ├── test_d2_download.py
│   ├── test_dependencies.py
│   ├── test_dependency_graph_model.py
│   ├── test_design_models.py
│   ├── test_diagram_backends.py
│   ├── test_diagrams_mermaid.py
│   ├── test_documents.py
│   ├── test_duplicate_names.py
│   ├── test_evals.py
│   ├── test_explain.py
│   ├── test_explain_check.py
│   ├── test_explain_config.py
│   ├── test_explain_status.py
│   ├── test_extra_designs_coverage.py
│   ├── test_facts.py
│   ├── test_facts_code.py
│   ├── test_facts_data_model.py
│   ├── test_facts_dominators.py
│   ├── test_functional_design.py
│   ├── test_generator.py
│   ├── test_grep_performance.py
│   ├── test_manifests.py
│   ├── test_max_lines_per_file.py
│   ├── test_output_dir.py
│   ├── test_plan_e2e.py
│   ├── test_plandoc.py
│   ├── test_properties.py
│   ├── test_raster.py
│   ├── test_render.py
│   ├── test_scaffold.py
│   ├── test_screenshots.py
│   ├── test_security_domain_designs.py
│   ├── test_skill.py
│   ├── test_skill_explaining_code.py
│   ├── test_skill_models.py
│   ├── test_skills_install.py
│   ├── test_source_dirs.py
│   ├── test_summary_slug_diagram_defaults.py
│   ├── test_technical_design.py
│   ├── test_templating_security.py
│   ├── test_threats.py
│   ├── test_verify.py
│   ├── test_verify_locate.py
│   ├── test_version.py
│   └── test_vscode_preview.py
├── .coverage
├── .featuredoc.yml
├── .gitignore
├── CHANGELOG.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

</details>
