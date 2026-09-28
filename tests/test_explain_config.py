"""Tests for the `explain.format` setting (arc42 by default, or the compact c4 format)."""

import pytest

from kingmadoc.config import (
    EXPLAIN_DOCUMENTS,
    EXPLAIN_FORMATS,
    EXPLAIN_MODELS,
    FeatureDocConfig,
    default_config_yaml,
    parse_config,
)
from kingmadoc.exceptions import ConfigError


def test_default_format_is_arc42() -> None:
    """Without configuration, explainers use arc42; `init` writes the setting."""
    assert FeatureDocConfig().explain.format == "arc42"
    assert EXPLAIN_FORMATS == ("arc42", "c4")
    assert "explain:\n  format: arc42" in default_config_yaml()


def test_c4_format_can_be_chosen() -> None:
    """The compact zoom-in format is the alternative."""
    assert parse_config({"explain": {"format": "c4"}}).explain.format == "c4"


@pytest.mark.parametrize(
    "data",
    [{"explain": {"format": "arc24"}}, {"explain": {"style": "c4"}}, {"explain": "arc42"}],
)
def test_invalid_explain_settings_are_rejected(data: dict) -> None:
    """Unknown formats and keys fail with the supported values."""
    with pytest.raises(ConfigError, match="explain"):
        parse_config(data)


def test_one_document_by_default_or_split() -> None:
    """One explainer by default; `split` writes a functional and a technical document."""
    assert FeatureDocConfig().explain.documents == "single"
    assert EXPLAIN_DOCUMENTS == ("single", "split", "functional", "technical")
    assert "  documents: single" in default_config_yaml()
    assert parse_config({"explain": {"documents": "split"}}).explain.documents == "split"


def test_unknown_documents_value_is_rejected() -> None:
    """Only single or split."""
    with pytest.raises(ConfigError, match="explain.documents"):
        parse_config({"explain": {"documents": "three"}})


def test_all_models_by_default_and_a_subset_can_be_chosen() -> None:
    """Every model we discussed is on by default; `explain.models` narrows the list."""
    assert FeatureDocConfig().explain.models == EXPLAIN_MODELS
    for name in ("use_case", "user_stories", "screens", "evil_user_stories", "threat_model",
                 "data_flow", "sequence", "er_diagram", "c4_context"):
        assert name in EXPLAIN_MODELS
    assert f"  models: [{', '.join(EXPLAIN_MODELS)}]" in default_config_yaml()
    chosen = parse_config({"explain": {"models": ["threat_model", "screens"]}})
    assert chosen.explain.models == ("threat_model", "screens")


@pytest.mark.parametrize("models", [["threat_modle"], "threat_model", [1]])
def test_unknown_or_malformed_explain_models_are_rejected(models: object) -> None:
    with pytest.raises(ConfigError, match="explain.models"):
        parse_config({"explain": {"models": models}})


def test_the_skill_names_every_explain_model() -> None:
    """The agent reads explain.models; every name is documented in the skill."""
    from pathlib import Path

    skill = Path(__file__).resolve().parents[1] / "skill" / "explaining-code"
    text = "".join(p.read_text(encoding="utf-8") for p in [skill / "SKILL.md",
                                                          *(skill / "reference").glob("*.md")])
    for name in EXPLAIN_MODELS:
        assert f"`{name}`" in text, name
