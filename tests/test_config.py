"""Tests for kingmadoc.config."""

from pathlib import Path

import pytest
import yaml

from kingmadoc.config import FeatureDocConfig, default_config_yaml, load_config, parse_config
from kingmadoc.exceptions import ConfigError


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    assert load_config(tmp_path) == FeatureDocConfig()


def test_file_overrides_defaults(tmp_path: Path) -> None:
    (tmp_path / ".featuredoc.yml").write_text(
        "output_dir: docs/design\nmax_questions: 2\nproject:\n  name: Demo\n",
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    assert config.output_dir == Path("docs/design")
    assert config.max_questions == 2
    assert config.project.name == "Demo"
    assert config.template == "plan_default.md.j2"


def test_default_yaml_matches_defaults() -> None:
    assert parse_config(yaml.safe_load(default_config_yaml())) == FeatureDocConfig()


def test_unknown_key_raises(tmp_path: Path) -> None:
    (tmp_path / ".featuredoc.yml").write_text("output_dri: x\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="output_dri"):
        load_config(tmp_path)
