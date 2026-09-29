# Skill evaluations

Do agents actually follow the KingmaDoc skills? Each scenario gives an agent a request on
a small fixture project and checks the result deterministically, with and without the
skills installed (roadmap WP5).

| Scenario | Skill | Request | Checks |
| --- | --- | --- | --- |
| [explain-feature](scenarios/explain-feature.yml) | `explaining-code` | Explain how placing an order works | explainer in `docs/explain/0001-*/`, arc42 headings, pictures only, at most three questions, no code changed |
| [explain-fo-to](scenarios/explain-fo-to.yml) | `explaining-code` | "Maak een FO en TO over de branch" (Dutch) | cover, `functional.md` (domain model, user stories, evil user stories) and `technical.md` (business rules, threat model, C4 level 2), `kingmadoc explain check`, no code changed |
| [explain-branch](scenarios/explain-branch.yml) | `explaining-code` | Explain what `feature/discount` changed | "What changed" about the discount, pictures only, no code changed |
| [plan-feature](scenarios/plan-feature.yml) | `kingmadoc` | Plan cancelling an order, don't build it | plan in `docs/features/`, plan headings, passes `kingmadoc check`, no code changed (the approval gate) |

The fixture is `fixtures/shop` (a small Django shop); `fixtures/shop-discount` is laid
over it on the branch.

## Running

```bash
python scripts/run_evals.py                          # all scenarios, with the skills
python scripts/run_evals.py --compare --record       # with and without; save the results
python scripts/run_evals.py plan-feature --repeat 3  # agents vary: run it three times
python scripts/run_evals.py explain-feature --keep /tmp/evals   # keep the workspaces
python scripts/run_evals.py explain-feature --check-only DIR    # only check a workspace
```

The agent is Claude Code (`claude -p`) by default. Its Bash is limited to `kingmadoc`,
read-only `git` and `ls`; the `kingmadoc` of this checkout is first on its `PATH`.
`--agent "<command with {request}>"` runs another agent. A run costs a real agent session
per scenario and variant, so it is not part of CI; `tests/test_evals.py` tests the
scenarios, the checks and the runner with a fake agent.

Results are saved as JSON in `results/` with `--record`, including the end of the
agent's reply and why an agent stopped (usage limit, max turns), apart from failed checks. Extend a skill only when a
recorded result shows a real failure.

## Results so far

| Run | explain-feature | explain-branch | plan-feature |
| --- | --- | --- | --- |
| [2026-09-27 11:18](results/2026-09-27T111837Z.json), with skill | 6/6 | 5/5 | 1/3 (asked its questions and stopped) |
| same run, without skill | 2/6 | 2/5 | 1/3 |
| [2026-09-27 11:26](results/2026-09-27T112600Z.json), with skill, 3 runs | | | 4/4, 4/4, 4/4 |

| [2026-09-28 06:45](results/2026-09-28T064505Z.json), skill 5.9 (before the optimisation) | 7/7, 173 s, $1.15 | 6/6, 100 s, $0.86 | FO/TO: stopped by the spend limit, D2 left unrendered |
| [2026-09-28 09:26](results/2026-09-28T092643Z.json), skill 6.0 (scaffold, shorter skill) | 7/7, 256 s, $1.54 | 6/6, 99 s, $0.81 | FO/TO: 8/8, 367 s, $2.10 |
| [2026-09-29 08:36](results/2026-09-29T083627Z.json) + [08:45](results/2026-09-29T084544Z.json), skill 6.1 | 7/7, 84 s, $0.53 | 6/6, 48 s, $0.32 | FO/TO: 8/8, 222 s, $1.07 |

The 6.1 rows are re-checked after the arc42 renumbering (section 2 "Starting situation") and
with Dutch FO headings accepted; the first 6.1 feature run picked the c4 format on its own,
which the skill now forbids. Rows from 2026-09-28 are re-checked with the current checks (`explain_check`,
`__pycache__` ignored, Dutch headings accepted). The 6.0 feature run filled the scaffold
placeholder by placeholder (41 turns instead of 22); the skill now says to write each
document in one pass: [2026-09-28 09:30](results/2026-09-28T093046Z.json), explain-feature
7/7, 192 s, $1.23, 20 turns, with the larger 6.0 content (user stories, rules, threat
model) at about the cost of the 5.9 run.

After the first run the plan scenario says the user cannot answer now (the skill's
non-interactive path). The baseline runs of 11:26 hit the account's spend limit and
did not run; they are not a result.
