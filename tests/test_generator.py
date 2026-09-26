"""Tests for kingmadoc.plan.generator."""

import doctest
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kingmadoc.config import AnalyzerConfig, FeatureDocConfig
from kingmadoc.naming import slugify
from kingmadoc.plan import generator
from kingmadoc.plan.analyzer import analyze
from kingmadoc.plan.generator import build_plan_context, render_plan, summarize

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Add login", "add-login"),
        ("  Café -- OAuth2 / SSO!  ", "cafe-oauth2-sso"),
        ("!!!", "feature"),
        ("a" * 50, "a" * 40),
        (
            "support exporting reports as csv and excel files",
            "support-exporting-reports-as-csv-and",
        ),
        (
            "one two three four five six seven eight nine",
            "one-two-three-four-five-six-seven-eight",
        ),
    ],
)
def test_slugify(text: str, expected: str) -> None:
    """Kebab-case, at most 40 chars, never ending mid-word or on a hyphen."""
    slug = slugify(text)

    assert slug == expected
    assert len(slug) <= 40


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Add login. Then logout.", "Add login."),
        ("Is it fast? Yes.", "Is it fast?"),
        ("No  sentence\n end", "No sentence end"),
        ("Version 1.2 support", "Version 1.2 support"),
    ],
)
def test_summarize_first_sentence(text: str, expected: str) -> None:
    """The summary is the first sentence, whitespace collapsed."""
    assert summarize(text) == expected


def test_summarize_caps_length_at_word_boundary() -> None:
    """Long sentences are cut at a word boundary and marked with an ellipsis."""
    summary = summarize("word " * 60)

    assert len(summary) <= 120
    assert summary.endswith("word…")


def test_build_plan_context_and_render(tmp_path: Path) -> None:
    """The context carries every field the template needs; rendering is deterministic."""
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    report = analyze(tmp_path, AnalyzerConfig())
    config = FeatureDocConfig()

    context = build_plan_context(
        "Add login.  With   MFA.", report, config, now=NOW, answers=[("Who?", "Admins")]
    )

    assert context.feature_summary == "Add login."
    assert context.feature_description == "Add login. With MFA."
    assert context.c4_context.startswith("```mermaid\nC4Context")
    assert context.c4_container.startswith("```mermaid\nC4Container")
    assert context.generated_at == NOW
    doc = render_plan(context, config)
    assert "2026-09-26T12:00+00:00" in doc
    assert "- **Who?** Admins" in doc
    assert render_plan(context, config) == doc


def test_docstring_examples() -> None:
    """The examples in the docstrings are real output."""
    result = doctest.testmod(generator)

    assert result.attempted == 4
    assert result.failed == 0
