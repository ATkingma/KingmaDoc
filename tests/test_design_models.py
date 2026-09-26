"""Tests for the per-document design model framework (roadmap WP8)."""

import pytest

from kingmadoc.config import DOCUMENT_MODELS, ExtraDesignsConfig, parse_config
from kingmadoc.exceptions import ConfigError, GenerationError
from kingmadoc.plan import models
from kingmadoc.plan.models import MODELS


def test_default_models_are_all_models_of_each_document() -> None:
    """Without configuration, every model of a document is selected."""
    defaults = ExtraDesignsConfig()

    for document, names in DOCUMENT_MODELS.items():
        assert getattr(defaults, document).models == names


def test_models_subset_is_parsed() -> None:
    """`models:` selects a subset, in the order given."""
    for document, names in DOCUMENT_MODELS.items():
        if len(names) < 2:
            continue
        subset = [names[1], names[0]]
        config = parse_config({"extra_designs": {document: {"models": subset}}})

        assert getattr(config.extra_designs, document).models == tuple(subset)


@pytest.mark.parametrize("document", ["functional_design", "technical_design"])
def test_unknown_model_is_rejected(document: str) -> None:
    """An unknown model name fails with the list of supported models."""
    with pytest.raises(ConfigError, match=r"Unknown model 'nope' in extra_designs\.\w+"):
        parse_config({"extra_designs": {document: {"models": ["nope"]}}})


@pytest.mark.parametrize("value", ["dependency_graph", [1], {"a": 1}])
def test_models_must_be_a_list_of_strings(value: object) -> None:
    """`models:` must be a list of strings."""
    with pytest.raises(ConfigError, match="models"):
        parse_config({"extra_designs": {"technical_design": {"models": value}}})


def test_registry_matches_config() -> None:
    """Every configurable model has a renderer, in the same document and order."""
    registered: dict[str, tuple[str, ...]] = {}
    for model in MODELS:
        registered[model.document] = (*registered.get(model.document, ()), model.name)

    assert {d: n for d, n in DOCUMENT_MODELS.items() if n} == registered


def test_registry_check_fails_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """The import-time check catches a model without config entry."""
    extra = models.Model("ghost", "technical_design", "Ghost", lambda context, backend: "")
    monkeypatch.setattr(models, "MODELS", (*MODELS, extra))

    with pytest.raises(GenerationError, match="ghost"):
        models._check_models()
