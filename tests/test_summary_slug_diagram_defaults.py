"""Regression tests for summaries, slugs and the context-diagram defaults (fix 7)."""

import pytest

from kingmadoc.diagrams import BACKENDS
from kingmadoc.naming import slugify
from kingmadoc.plan.generator import feature_slug, summarize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Add export, e.g. CSV and Excel, to reports.",
            "Add export, e.g. CSV and Excel, to reports.",
        ),
        ("Support files, i.e. PDF only. Later more.", "Support files, i.e. PDF only."),
        ("Import users, groups, etc. Then sync.", "Import users, groups, etc. Then sync."),
        ("Compare A vs. B in the report.", "Compare A vs. B in the report."),
        (
            "See the old flow, cf. Section 2, and fix it.",
            "See the old flow, cf. Section 2, and fix it.",
        ),
        ("Cache for approx. Ten minutes per user.", "Cache for approx. Ten minutes per user."),
        ("Add login. then logout", "Add login. then logout"),
        ("Add login. Then logout.", "Add login."),
    ],
)
def test_summary_skips_abbreviations_and_lowercase_continuations(text: str, expected: str) -> None:
    """A sentence ends only before a capital letter, and never at a known abbreviation."""
    assert summarize(text) == expected


def test_non_latin_descriptions_get_distinct_slugs() -> None:
    """Descriptions that transliterate to nothing get a stable hash, not a shared `feature`."""
    first = feature_slug("Добавить вход через почту.")
    second = feature_slug("添加登录")

    assert first != second
    assert first.startswith("feature-") and second.startswith("feature-")
    assert first == feature_slug("Добавить вход через почту.")  # deterministic


def test_accents_are_transliterated() -> None:
    """Accented Latin letters keep their base letter instead of being dropped."""
    assert slugify("Café crème brûlée") == "cafe-creme-brulee"


@pytest.mark.parametrize("fmt", BACKENDS)
def test_context_default_relationships_flag(fmt: str) -> None:
    """Defaults are controlled by `default_relationships`, and explicit ones are added to them."""
    backend = BACKENDS[fmt]
    actors, externals = [{"name": "Customer"}], [{"name": "Stripe"}]
    explicit = [("Customer", "Stripe", "Pays via")]

    both = backend.render_context("Shop", actors, externals, relationships=explicit)
    only_explicit = backend.render_context(
        "Shop", actors, externals, relationships=explicit, default_relationships=False
    )
    none = backend.render_context("Shop", actors, externals, default_relationships=False)

    assert "Uses" in both and "Pays via" in both
    assert "Uses" not in only_explicit and "Pays via" in only_explicit
    assert "Uses" not in none and "Pays via" not in none
