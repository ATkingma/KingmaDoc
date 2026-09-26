"""Regression test: import scanning is linear, even on hostile input."""

import time
from pathlib import Path

from kingmadoc.config import AnalyzerConfig
from kingmadoc.plan.analyzer import analyze


def test_many_blank_lines_are_scanned_quickly(tmp_path: Path) -> None:
    """`^\\s*` patterns backtracked over blank-line runs: 80k blank lines took ~28 s each."""
    (tmp_path / "app.py").write_text("\n" * 50_000 + "import django\n", encoding="utf-8")

    start = time.perf_counter()
    # Read every line, so the per-file line limit doesn't hide a regex regression.
    report = analyze(tmp_path, AnalyzerConfig(max_lines_per_file=100_000))
    elapsed = time.perf_counter() - start

    assert "Django" in report.detected_stack
    assert elapsed < 2.0, f"analysis took {elapsed:.1f} s"


def test_indented_and_spaced_imports_still_match(tmp_path: Path) -> None:
    """Indentation and extra spaces/tabs before and inside import lines still count."""
    (tmp_path / "a.py").write_text("if True:\n\t from  flask import Flask\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("    import\tfastapi\n", encoding="utf-8")

    stack = analyze(tmp_path, AnalyzerConfig()).detected_stack

    assert "Flask" in stack and "FastAPI" in stack
