"""Tests for kingmadoc.plan.analyzer."""

import json
from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.config import AnalyzerConfig
from kingmadoc.plan.analyzer import analyze, detect_stack_from_manifests, report_to_dict


def _write(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_empty_dir(tmp_path: Path) -> None:
    """An empty directory yields an empty report."""
    report = analyze(tmp_path, AnalyzerConfig())

    assert report.root == tmp_path.resolve()
    assert report.file_count == 0
    assert dict(report.language_breakdown) == {}
    assert report.top_level_dirs == ()
    assert report.entry_points == ()
    assert report.config_files == ()
    assert report.test_dirs == ()
    assert report.detected_stack == ()
    assert report.primary_language is None
    assert not report.truncated


def test_single_python_file(tmp_path: Path) -> None:
    """A lone ``main.py`` is Python and an entry point."""
    _write(tmp_path, {"main.py": "import fastapi\n"})

    report = analyze(tmp_path, AnalyzerConfig())

    assert report.file_count == 1
    assert dict(report.language_breakdown) == {"python": 1}
    assert report.top_level_dirs == ()
    assert report.entry_points == ("main.py",)
    assert report.detected_stack == ("FastAPI", "Python")
    assert report.primary_language == "Python"


def test_mixed_repo(tmp_path: Path) -> None:
    """Languages, entry points, configs, tests and stack across a Python + TS repo."""
    _write(tmp_path, {
        "pyproject.toml": (
            '[project]\nname = "api"\n'
            'dependencies = ["FastAPI[all]>=0.110", "psycopg2-binary", "SQLAlchemy~=2.0"]\n'
        ),
        "requirements.txt": "# pinned\nredis==5.0\n-r other.txt\n",
        "docker-compose.yml": (
            "services:\n  db:\n    image: postgres:16\n  cache:\n    image: bitnami/redis\n"
        ),
        "README.md": "# Demo\n",
        "docs/guide.md": "Guide\n",
        "api/app.py": "from fastapi import FastAPI\n",
        "api/models.py": "x = 1\n",
        "tests/test_app.py": "def test(): pass\n",
        "tests/unit/main.py": "",
        "frontend/package.json": json.dumps(
            {"dependencies": {"react": "^18"}, "devDependencies": {"typescript": "^5"}}
        ),
        "frontend/src/index.ts": "export {}\n",
        "frontend/src/__tests__/index.test.ts": "",
        "go.mod": "module example.com/x\n\ngo 1.22\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.1\n)\n",
        "Cargo.toml": '[package]\nname = "x"\n\n[dependencies]\naxum = "0.7"\n',
        # Ignored directories must not count.
        "node_modules/react/index.js": "",
        ".venv/lib/site.py": "",
        ".git/config": "",
        "dist/bundle.js": "",
        "build/out.py": "",
        "api/__pycache__/app.cpython-311.pyc": "",
    })

    report = analyze(tmp_path, AnalyzerConfig(exclude_dirs=()))

    assert report.file_count == 14
    assert dict(report.language_breakdown) == {
        "python": 4, "markdown": 2, "typescript": 2, "json": 1, "toml": 2, "yaml": 1,
    }
    assert list(report.language_breakdown)[0] == "python"
    assert report.top_level_dirs == ("api", "docs", "frontend", "tests")
    assert report.entry_points == ("api/app.py", "frontend/src/index.ts")
    assert report.config_files == (
        "Cargo.toml", "docker-compose.yml", "frontend/package.json", "go.mod",
        "pyproject.toml", "requirements.txt",
    )
    assert report.test_dirs == ("frontend/src/__tests__", "tests")
    assert {
        "Python", "TypeScript", "FastAPI", "PostgreSQL", "SQLAlchemy", "Redis",
        "React", "Gin", "Axum", "Docker Compose", "Node.js", "Go", "Rust",
    } <= set(report.detected_stack)
    assert list(report.detected_stack) == sorted(report.detected_stack)
    assert report.primary_language == "Python"


def test_file_limit_truncates(tmp_path: Path) -> None:
    """The walk stops at ``max_files`` and flags the report as truncated."""
    _write(tmp_path, {f"f{i}.py": "" for i in range(5)})

    report = analyze(tmp_path, AnalyzerConfig(max_files=3))

    assert report.file_count == 3
    assert report.truncated


def test_malformed_manifests_are_ignored() -> None:
    """Broken manifests contribute nothing instead of raising."""
    assert detect_stack_from_manifests({
        "pyproject.toml": "[project",
        "package.json": "{",
        "docker-compose.yml": "services: [",
        "Cargo.toml": "= =",
    }) == set()


def test_plan_json_outputs_report(tmp_path: Path) -> None:
    """``analyze --json`` prints the report."""
    _write(tmp_path, {"main.py": ""})

    result = CliRunner().invoke(cli, ["analyze", "--json", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data == report_to_dict(analyze(tmp_path, AnalyzerConfig()))
    assert data["entry_points"] == ["main.py"]
    assert not (tmp_path / "docs").exists()
