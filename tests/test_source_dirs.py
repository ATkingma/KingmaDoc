"""Regression tests: test directories are never C4 containers."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.config import AnalyzerConfig
from kingmadoc.plan.analyzer import analyze


def _touch(root: Path, *files: str) -> None:
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")


@pytest.mark.parametrize("test_dir", ["__tests__", "spec", "specs", "tests", "test"])
def test_top_level_test_dirs_are_not_source(tmp_path: Path, test_dir: str) -> None:
    """Every test directory name is excluded at the top level."""
    _touch(tmp_path, "app/index.js", f"{test_dir}/a.test.js")

    assert analyze(tmp_path, AnalyzerConfig()).source_dirs == (Path("app"),)


def test_test_dirs_inside_src_are_not_source(tmp_path: Path) -> None:
    """`src/tests` is not a source module next to `src/pkg`."""
    _touch(tmp_path, "src/pkg/a.py", "src/tests/test_a.py", "src/__tests__/b.test.js")

    assert analyze(tmp_path, AnalyzerConfig()).source_dirs == (Path("src/pkg"),)


def test_src_files_next_to_packages(tmp_path: Path) -> None:
    """Loose files in src/ don't add a `src` container when src/ has packages."""
    _touch(tmp_path, "src/main.py", "src/pkg/a.py")

    assert analyze(tmp_path, AnalyzerConfig()).source_dirs == (Path("src/pkg"),)


def test_flat_src_layout_is_one_container(tmp_path: Path) -> None:
    """A src/ with only loose files is still one source module."""
    _touch(tmp_path, "src/main.py", "src/util.py")

    assert analyze(tmp_path, AnalyzerConfig()).source_dirs == (Path("src"),)


def test_user_arrow_points_at_real_code(tmp_path: Path) -> None:
    """The reported case: `__tests__` sorted first and got the User arrow."""
    _touch(tmp_path, "app/index.js", "__tests__/a.test.js")

    result = CliRunner().invoke(
        cli, ["plan", "Add x.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )

    assert result.exit_code == 0, result.output
    assert "__tests__" not in result.stdout.split("## Appendix")[0]
    assert 'Rel(user, app, "Uses")' in result.stdout
