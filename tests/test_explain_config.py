"""Tests for the `explain.format` setting (arc42 by default, or the compact c4 format)."""

import pytest

from kingmadoc.config import EXPLAIN_FORMATS, FeatureDocConfig, default_config_yaml, parse_config
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
