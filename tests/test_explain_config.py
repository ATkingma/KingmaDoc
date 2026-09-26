"""Tests for the `explain.format` setting (arc42 by default, or the compact c4 format)."""

import pytest

from kingmadoc.config import (
    EXPLAIN_DOCUMENTS,
    EXPLAIN_FORMATS,
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
    assert EXPLAIN_DOCUMENTS == ("single", "split")
    assert "  documents: single" in default_config_yaml()
    assert parse_config({"explain": {"documents": "split"}}).explain.documents == "split"


def test_unknown_documents_value_is_rejected() -> None:
    """Only single or split."""
    with pytest.raises(ConfigError, match="explain.documents"):
        parse_config({"explain": {"documents": "three"}})
