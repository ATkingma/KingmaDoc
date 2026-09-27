"""Property-based tests (Hypothesis) for the parsers that read text KingmaDoc does not
control: descriptions, plan docs, config files and source code (roadmap WP7, G3)."""

import json
import re

from hypothesis import given, settings
from hypothesis import strategies as st

from kingmadoc.explain import Entry, index_markdown
from kingmadoc.facts.data_model import data_model
from kingmadoc.facts.js_modules import _without_comments, js_dependencies
from kingmadoc.facts.projects import project_references
from kingmadoc.facts.routes import routes
from kingmadoc.naming import MAX_SLUG_LENGTH, slugify
from kingmadoc.plan.generator import MAX_SUMMARY_LENGTH, summarize
from kingmadoc.plandoc import STATUSES, check_plan, parse_plan, set_status
from kingmadoc.verify.locate import SLUG_PATTERN

SOURCE_NAMES = st.sampled_from([
    "a.py", "urls.py", "b.cs", "Program.cs", "c.ts", "d.tsx", "e.js", "schema.prisma",
    "app/page.tsx", "app/api/x/route.ts", "pages/api/y.ts", "tsconfig.json", "X.csproj",
])
settings.register_profile("kingmadoc", max_examples=150, deadline=None)
settings.load_profile("kingmadoc")


@given(st.text())
def test_slugify_always_gives_a_valid_short_slug(text: str) -> None:
    """Any description gives a kebab-case slug that fits in a file name."""
    slug = slugify(text)

    assert SLUG_PATTERN.fullmatch(slug), slug
    assert len(slug) <= MAX_SLUG_LENGTH


@given(st.text())
def test_summary_is_one_short_line(text: str) -> None:
    """The summary never spans lines and never exceeds its maximum length."""
    summary = summarize(text)

    assert "\n" not in summary
    assert len(summary) <= MAX_SUMMARY_LENGTH


@given(st.text())
def test_check_plan_never_crashes(text: str) -> None:
    """Hand-edited plans can hold anything: check reports problems, it does not raise."""
    assert isinstance(check_plan(text), list)
    assert isinstance(check_plan("---\n" + text + "\n---\n# Feature: x\n"), list)


@given(
    slug=st.from_regex(SLUG_PATTERN, fullmatch=True),
    count=st.integers(min_value=0, max_value=5),
    status=st.sampled_from(STATUSES),
    new=st.sampled_from(STATUSES),
)
def test_valid_plans_pass_and_keep_their_text_when_the_status_changes(
    slug: str, count: int, status: str, new: str
) -> None:
    """A well-formed plan passes check; set_status changes only the status."""
    ids = [f"REQ-{n}" for n in range(1, count + 1)]
    text = (
        f"---\nkingmadoc: 1\nfeature: \"{slug}\"\nstatus: {status}\n"
        f"requirements: [{', '.join(ids)}]\nfiles_expected: []\n---\n# Feature: x\n\n"
        f"| **Status** | {status.capitalize()} |\n\n"
        + "".join(f"- **{i}**: THE SYSTEM SHALL work.\n" for i in ids)
    )

    assert check_plan(text, slug=slug) == []
    changed = set_status(text, new)
    assert parse_plan(changed).status == new
    assert check_plan(changed, slug=slug) == []
    assert changed.count("\n") == text.count("\n")


@given(st.dictionaries(SOURCE_NAMES, st.text(), max_size=4))
def test_code_parsers_never_crash(sources: dict[str, str]) -> None:
    """Routes, data model, JS/TS modules and project references accept any source text."""
    routes(sources)
    data_model(sources)
    js_dependencies(sources)
    project_references(sources)


JSON_VALUES = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children, max_size=3)
    | st.dictionaries(st.text(), children, max_size=3),
    max_leaves=10,
)


@given(JSON_VALUES)
def test_comment_stripping_keeps_json_without_comments(value: object) -> None:
    """Strings with "//" or "/*" (globs, URLs) are data: plain JSON passes through intact."""
    text = json.dumps(value)

    assert json.loads(_without_comments(text)) == value


@given(st.text(), st.text())
def test_index_rows_keep_their_four_cells(name: str, scope: str) -> None:
    """Whatever a title contains (| ] \\r from CRLF files), the index row stays one row
    of four cells."""
    index = index_markdown([Entry("0001", "0001-x/README.md", name, scope, "2026-09-27")])
    rows = [line for line in re.split(r"\r\n|\r|\n", index) if line.startswith("| 0001 |")]

    assert len(rows) == 1
    assert len(re.findall(r"(?<!\\)\|", rows[0].replace("\\\\", ""))) == 5
    assert not re.search(r"[\r\x85\u2028\u2029]", index)


def test_every_module_is_under_the_click_contract() -> None:
    """A new module must be listed in the E1 import-linter contract (pyproject.toml)."""
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    contract = next(c for c in config["tool"]["importlinter"]["contracts"]
                    if c["name"].startswith("Only the CLI imports click"))
    package = root / "src" / "kingmadoc"
    modules = {f"kingmadoc.{p.stem}" for p in package.glob("*.py")
               if p.stem not in ("__init__", "__main__", "cli")}
    modules |= {f"kingmadoc.{p.name}" for p in package.iterdir()
                if p.is_dir() and (p / "__init__.py").is_file()}

    assert modules <= set(contract["source_modules"]), modules - set(contract["source_modules"])
