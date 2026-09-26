"""Tests for the import-time check that EXTRA_DESIGNS matches ExtraDesignsConfig (fix 6)."""

from dataclasses import fields

import pytest

from kingmadoc.config import ExtraDesignsConfig
from kingmadoc.exceptions import GenerationError
from kingmadoc.plan import generator
from kingmadoc.plan.generator import EXTRA_DESIGNS, ExtraDesign


def test_registry_matches_config_fields() -> None:
    """Every extra design has a config field and vice versa."""
    assert sorted(d.name for d in EXTRA_DESIGNS) == sorted(
        f.name for f in fields(ExtraDesignsConfig)
    )


def test_unknown_design_name_fails_the_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """A registry entry without a config field is rejected."""
    monkeypatch.setattr(
        generator, "EXTRA_DESIGNS", (*EXTRA_DESIGNS, ExtraDesign("api_design", "-api.md"))
    )

    with pytest.raises(GenerationError, match="api_design"):
        generator._check_extra_designs()


def test_missing_design_fails_the_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """A config field without a registry entry is rejected too."""
    monkeypatch.setattr(generator, "EXTRA_DESIGNS", EXTRA_DESIGNS[:1])

    with pytest.raises(GenerationError, match="technical_design"):
        generator._check_extra_designs()
