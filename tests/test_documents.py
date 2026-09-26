"""Tests for kingmadoc.documents: multi-file writes are all-or-nothing (fix 4)."""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc import documents
from kingmadoc.cli import cli
from kingmadoc.documents import write_document, write_documents
from kingmadoc.exceptions import GenerationError


def test_phase1_failure_writes_nothing(tmp_path: Path) -> None:
    """A directory in place of a target fails validation; the plan is not written either."""
    (tmp_path / ".featuredoc.yml").write_text(
        "extra_designs:\n  functional_design: {enabled: true}\n", encoding="utf-8"
    )
    features = tmp_path / "docs" / "features"
    (features / "add-x-functional-design.md").mkdir(parents=True)

    result = CliRunner().invoke(
        cli, ["plan", "Add x.", "--root", str(tmp_path), "--no-input", "--force"]
    )

    assert not (features / "add-x-plan.md").exists()
    assert result.exit_code == 1
    assert "is a directory" in result.output


def test_phase3_failure_leaves_existing_files_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If moving the second file into place fails, the first file is rolled back."""
    first, second = tmp_path / "a.md", tmp_path / "b.md"
    first.write_text("old a", encoding="utf-8")
    second.write_text("old b", encoding="utf-8")
    real_replace = os.replace

    def failing_replace(src: os.PathLike, dst: os.PathLike) -> None:
        if Path(dst) == second and Path(src).name.endswith(".tmp"):
            raise OSError("disk full")
        real_replace(src, dst)

    monkeypatch.setattr(documents.os, "replace", failing_replace)

    with pytest.raises(GenerationError, match="disk full"):
        write_documents([(first, "new a"), (second, "new b")], overwrite=True)

    assert first.read_text(encoding="utf-8") == "old a"
    assert second.read_text(encoding="utf-8") == "old b"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.md", "b.md"]  # no temp files


def test_phase3_failure_removes_new_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Files that did not exist before are removed again on failure."""
    first, second = tmp_path / "new" / "a.md", tmp_path / "new" / "b.md"
    real_replace = os.replace

    def failing_replace(src: os.PathLike, dst: os.PathLike) -> None:
        if Path(dst) == second:
            raise OSError("disk full")
        real_replace(src, dst)

    monkeypatch.setattr(documents.os, "replace", failing_replace)

    with pytest.raises(GenerationError):
        write_documents([(first, "a"), (second, "b")])

    assert not (tmp_path / "new").exists()  # created directory removed too


def test_write_document_takes_path_then_content(tmp_path: Path) -> None:
    """Both functions take (path, content), in that order."""
    path = write_document(tmp_path / "doc.md", "hello")

    assert path.read_text(encoding="utf-8") == "hello"
