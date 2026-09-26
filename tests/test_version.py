"""Tests for `kingmadoc --version`: it shows which commit is installed."""

import json

import pytest
from click.testing import CliRunner

from kingmadoc import __version__, about
from kingmadoc.cli import cli


class _Dist:
    def __init__(self, direct_url: dict | None) -> None:
        self._text = None if direct_url is None else json.dumps(direct_url)

    def read_text(self, name: str) -> str | None:
        return self._text if name == "direct_url.json" else None


@pytest.mark.parametrize(
    ("direct_url", "suffix"),
    [
        (
            {"url": "https://github.com/x/y", "vcs_info": {"commit_id": "29244f74cac0"}},
            " (git 29244f7)",
        ),
        ({"url": "file:///src", "dir_info": {"editable": True}}, " (editable)"),
        (None, ""),
    ],
)
def test_version_text(
    monkeypatch: pytest.MonkeyPatch, direct_url: dict[str, object] | None, suffix: str
) -> None:
    """A git install shows its commit, an editable install says so, a wheel shows the version."""
    monkeypatch.setattr(about, "_distribution", lambda: _Dist(direct_url))

    assert about.version_text() == f"{__version__}{suffix}"


def test_cli_version_includes_the_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """`kingmadoc --version` prints the same text."""
    monkeypatch.setattr(about, "_distribution", lambda: _Dist(
        {"url": "https://github.com/x/y", "vcs_info": {"vcs": "git", "commit_id": "abcdef123"}}
    ))

    result = CliRunner().invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"kingmadoc, version {__version__} (git abcdef1)"


def test_version_is_a_development_version() -> None:
    """Unreleased work is marked as such, so an update is visible in the version."""
    assert __version__ == "0.2.0.dev0"
