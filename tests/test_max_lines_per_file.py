"""Tests for analyzer.max_lines_per_file (lines read per file when scanning imports)."""

from pathlib import Path

import pytest

from kingmadoc.config import AnalyzerConfig, default_config_yaml, load_config, parse_config
from kingmadoc.exceptions import ConfigError
from kingmadoc.plan.analyzer import analyze


def _file_with_import_on_line(root: Path, line: int) -> None:
    (root / "app.py").write_text("x = 1\n" * (line - 1) + "import django\n", encoding="utf-8")


def test_default_is_2000_and_in_init_output() -> None:
    """The default is 2000 lines and `kingmadoc init` writes it out."""
    assert AnalyzerConfig().max_lines_per_file == 2000
    assert "max_lines_per_file: 2000" in default_config_yaml()


def test_imports_within_the_limit_are_found(tmp_path: Path) -> None:
    """An import on line 100 counts when the limit is 100."""
    _file_with_import_on_line(tmp_path, 100)

    report = analyze(tmp_path, AnalyzerConfig(max_lines_per_file=100))

    assert "Django" in report.detected_stack


def test_lines_beyond_the_limit_are_not_read(tmp_path: Path) -> None:
    """An import on line 101 is ignored when the limit is 100 (set via the config file)."""
    _file_with_import_on_line(tmp_path, 101)
    (tmp_path / ".featuredoc.yml").write_text(
        "analyzer:\n  max_lines_per_file: 100\n", encoding="utf-8"
    )

    report = analyze(tmp_path, load_config(tmp_path).analyzer)

    assert "Django" not in report.detected_stack


def test_manifests_are_not_limited(tmp_path: Path) -> None:
    """The limit is for import scanning only; manifests are always read in full."""
    deps = "".join(f'  "pkg{i}",\n' for i in range(50)) + '  "fastapi",\n'
    (tmp_path / "pyproject.toml").write_text(
        f"[project]\ndependencies = [\n{deps}]\n", encoding="utf-8"
    )

    report = analyze(tmp_path, AnalyzerConfig(max_lines_per_file=10))

    assert "FastAPI" in report.detected_stack


@pytest.mark.parametrize("value", [0, -1, "many", True])
def test_invalid_values_are_rejected(value: object) -> None:
    """Only positive integers are accepted."""
    with pytest.raises(ConfigError, match="max_lines_per_file"):
        parse_config({"analyzer": {"max_lines_per_file": value}})
