"""Regression tests: date-named files in docs/adr don't hijack ADR numbering."""

from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli


def _project(tmp_path: Path, files: dict[str, str]) -> Path:
    (tmp_path / ".featuredoc.yml").write_text("adr:\n  enabled: true\n", encoding="utf-8")
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    for name, text in files.items():
        (adr_dir / name).write_text(text, encoding="utf-8")
    return adr_dir


def _adr(root: Path, title: str) -> str:
    result = CliRunner().invoke(cli, ["adr", title, "--root", str(root)])
    assert result.exit_code == 0, result.output
    return Path(result.stdout.strip()).name


def test_date_named_file_is_not_an_adr(tmp_path: Path) -> None:
    """The reported case: `2024-q3-review.md` made the next ADR 2025."""
    _project(tmp_path, {"0001-use-postgres.md": "# 0001. Use Postgres\n",
                        "2024-q3-review.md": "# Q3 review\n"})

    assert _adr(tmp_path, "Drop Redis") == "0002-drop-redis.md"


def test_a_real_adr_with_a_year_like_number_still_counts(tmp_path: Path) -> None:
    """ADR 2024 exists when its heading says so."""
    _project(tmp_path, {"2024-big-decision.md": "# 2024. Big decision\n"})

    assert _adr(tmp_path, "Next") == "2025-next.md"


def test_custom_template_adrs_without_number_heading_count(tmp_path: Path) -> None:
    """Numbers outside the year range count regardless of the heading (custom templates)."""
    _project(tmp_path, {f"000{n}-x{n}.md": f"# Decision {n}\n" for n in (1, 2, 3)})

    assert _adr(tmp_path, "Fourth") == "0004-fourth.md"
