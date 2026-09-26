"""Regression tests for manifest parsing in the analyzer (fix 5)."""

import json
from pathlib import Path

import pytest

from kingmadoc.config import AnalyzerConfig
from kingmadoc.plan.analyzer import analyze, detect_stack_from_manifests

MALFORMED = {
    "pyproject: dependencies is an int": ("pyproject.toml", "[project]\ndependencies = 5\n"),
    "pyproject: optional group is an int": (
        "pyproject.toml", "[project.optional-dependencies]\ndev = 5\n"),
    "pyproject: optional-dependencies is a list": (
        "pyproject.toml", '[project]\noptional-dependencies = ["x"]\n'),
    "pyproject: dependency-groups entry is a string": (
        "pyproject.toml", '[dependency-groups]\ndev = "pytest"\n'),
    "pyproject: poetry group is a list": ("pyproject.toml", "[tool.poetry]\ngroup = [1]\n"),
    "package.json: root is a list": ("package.json", '["react"]'),
    "package.json: dependencies is a list": ("package.json", '{"dependencies": ["react"]}'),
    "Cargo: target is a list": ("Cargo.toml", "target = [1, 2]\n"),
    "Cargo: workspace.dependencies is a string": (
        "Cargo.toml", '[workspace]\ndependencies = "axum"\n'),
    "compose: services is a list": ("docker-compose.yml", "services: [a, b]\n"),
    "compose: image is a list": ("docker-compose.yml", "services:\n  db:\n    image: [1]\n"),
}


@pytest.mark.parametrize(("name", "text"), MALFORMED.values(), ids=MALFORMED.keys())
def test_malformed_manifest_is_skipped(name: str, text: str) -> None:
    """Wrong types inside a manifest are skipped silently, never a crash."""
    assert isinstance(detect_stack_from_manifests({name: text}), set)


def test_malformed_pyproject_does_not_crash_plan_analysis(tmp_path: Path) -> None:
    """The reported crash: `[project] dependencies = 5` made analysis raise TypeError."""
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = 5\n", encoding="utf-8")

    report = analyze(tmp_path, AnalyzerConfig())

    assert report.detected_stack == ("Python",)


@pytest.mark.parametrize(
    ("name", "text", "tech"),
    [
        ("package.json", json.dumps({"dependencies": {"react": "18"}}), "React"),
        ("pyproject.toml", '[project]\ndependencies = ["fastapi"]\n', "FastAPI"),
        ("Cargo.toml", '[dependencies]\naxum = "0.7"\n', "Axum"),
    ],
)
def test_manifest_with_utf8_bom_is_read(tmp_path: Path, name: str, text: str, tech: str) -> None:
    """Manifests saved with a UTF-8 BOM (common on Windows) are parsed, not skipped."""
    (tmp_path / name).write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))

    assert tech in analyze(tmp_path, AnalyzerConfig()).detected_stack


NEW_TABLES = {
    "Cargo [workspace.dependencies]": (
        "Cargo.toml", '[workspace.dependencies]\naxum = "0.7"\n', "Axum"),
    "Cargo [target.*.dependencies]": (
        "Cargo.toml", "[target.'cfg(unix)'.dependencies]\ntokio = \"1\"\n", "Tokio"),
    "PEP 735 [dependency-groups]": (
        "pyproject.toml",
        '[dependency-groups]\ndev = ["SQLAlchemy>=2", {include-group = "test"}]\n',
        "SQLAlchemy"),
    "Poetry [tool.poetry.group.*.dependencies]": (
        "pyproject.toml", '[tool.poetry.group.web.dependencies]\nflask = "^3"\n', "Flask"),
    "npm optionalDependencies": (
        "package.json", json.dumps({"optionalDependencies": {"pg": "8"}}), "PostgreSQL"),
    "npm devDependencies": (
        "package.json", json.dumps({"devDependencies": {"typescript": "5"}}), "TypeScript"),
    "npm peerDependencies": (
        "package.json", json.dumps({"peerDependencies": {"react": "18"}}), "React"),
}


@pytest.mark.parametrize(("name", "text", "tech"), NEW_TABLES.values(), ids=NEW_TABLES.keys())
def test_dependency_table_is_read(name: str, text: str, tech: str) -> None:
    """Each supported dependency table contributes to the detected stack."""
    assert tech in detect_stack_from_manifests({name: text})


@pytest.mark.parametrize(
    "image",
    [
        "registry.local:5000/postgres:16",
        "registry.local:5000/library/postgres",
        "postgres:16",
        "postgres@sha256:abc123",
        "docker.io/bitnami/postgresql:16.2.0",
    ],
)
def test_compose_image_name(image: str) -> None:
    """The image name is the last path segment without tag or digest, even with a registry port."""
    compose = f"services:\n  db:\n    image: {image}\n"

    assert detect_stack_from_manifests({"compose.yaml": compose}) == {"PostgreSQL"}
