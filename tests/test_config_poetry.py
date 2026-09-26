"""Tests for Poetry dependency parsing in pyproject.toml."""

from pathlib import Path

from kingmadoc.config import AnalyzerConfig
from kingmadoc.plan.analyzer import analyze, detect_stack_from_manifests

POETRY = """\
[tool.poetry]
name = "shop"

[tool.poetry.dependencies]
python = "^3.11"
FastAPI = {version = "^0.110", extras = ["all"]}
psycopg2-binary = "^2.9"

[tool.poetry.group.dev.dependencies]
pytest = "^8"

[tool.poetry.group.jobs.dependencies]
celery = "^5"
"""


def test_poetry_main_and_group_dependencies() -> None:
    """Main and group dependencies are read; names are normalized; `python` is ignored."""
    assert detect_stack_from_manifests({"pyproject.toml": POETRY}) == {
        "FastAPI",
        "PostgreSQL",
        "Celery",
    }


def test_poetry_project_through_analyze(tmp_path: Path) -> None:
    """A Poetry project is detected end to end."""
    (tmp_path / "pyproject.toml").write_text(POETRY, encoding="utf-8")

    report = analyze(tmp_path, AnalyzerConfig())

    assert set(report.detected_stack) == {"Python", "FastAPI", "PostgreSQL", "Celery"}
    assert report.config_files == ("pyproject.toml",)


def test_poetry_tables_with_wrong_types_are_ignored() -> None:
    """Malformed Poetry tables contribute nothing and do not raise."""
    broken = '[tool.poetry]\ndependencies = ["fastapi"]\ngroup = "dev"\n'

    assert detect_stack_from_manifests({"pyproject.toml": broken}) == set()
