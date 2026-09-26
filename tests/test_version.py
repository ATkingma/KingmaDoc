"""Tests for `kingmadoc --version`: it shows which commit is installed."""

import json
import re
import tomllib
from importlib import metadata
from pathlib import Path

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


def test_version_comes_from_the_installed_package() -> None:
    """The version is set at build time from the git tag (hatch-vcs), not by hand."""
    assert __version__ == metadata.version("kingmadoc")
    assert re.fullmatch(r"\d+\.\d+\.\d+(\.dev\d+|(a|b|rc)\d+)?", __version__), __version__


def test_pyproject_takes_the_version_from_git() -> None:
    """Commits after a tag get a higher dev version, so `pipx upgrade` sees every update."""
    config = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text("utf-8"))
    version = config["tool"]["hatch"]["version"]

    assert version["source"] == "vcs"
    assert version["raw-options"]["local_scheme"] == "no-local-version"


@pytest.mark.parametrize("raw", ["{not json", '{"vcs_info": "git"}', '{"dir_info": []}', "[]"])
def test_a_malformed_direct_url_shows_the_plain_version(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    """--version never crashes on an odd direct_url.json."""

    class _Raw:
        def read_text(self, name: str) -> str:
            return raw

    monkeypatch.setattr(about, "_distribution", lambda: _Raw())

    assert about.version_text() == __version__
