"""``kingmadoc screenshots``: screens of a running app, Playwright or npx."""

import builtins
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc import screenshots
from kingmadoc.cli import cli
from kingmadoc.exceptions import ScreenshotError
from kingmadoc.screenshots import Screen, capture, parse_screens, screen_url


def test_screens_are_route_and_name() -> None:
    assert parse_screens(["/contact=screen-us-1", "/orders/", "/"]) == [
        Screen("/contact", "screen-us-1"), Screen("/orders/", "orders"), Screen("/", "home"),
    ]
    with pytest.raises(ScreenshotError):
        parse_screens([])
    with pytest.raises(ScreenshotError):
        parse_screens(["=x"])


def test_only_http_urls() -> None:
    assert screen_url("http://localhost:8000", "/contact") == "http://localhost:8000/contact"
    assert screen_url("http://localhost:8000/app/", "orders") == "http://localhost:8000/app/orders"
    for bad in ("file:///etc/passwd", "javascript:alert(1)", "localhost:8000"):
        with pytest.raises(ScreenshotError):
            screen_url(bad, "/")


def _no_playwright(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name.startswith("playwright"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_falls_back_to_npx(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Without the Playwright package, one npx call per screen, with a fixed argv."""
    _no_playwright(monkeypatch)
    monkeypatch.setattr(screenshots.shutil, "which", lambda _name: "/usr/bin/npx")
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        Path(command[-1]).write_bytes(b"\x89PNG")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(screenshots.subprocess, "run", fake_run)

    paths = capture("http://localhost:8000", parse_screens(["/a=one", "/b=two"]), tmp_path)

    assert paths == [tmp_path / "one.png", tmp_path / "two.png"]
    assert calls[0][:4] == ["/usr/bin/npx", "-y", "playwright", "screenshot"]
    assert "--viewport-size=1280,800" in calls[0]
    assert calls[0][-2:] == ["http://localhost:8000/a", str(tmp_path / "one.png")]


def test_npx_failures_are_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _no_playwright(monkeypatch)
    monkeypatch.setattr(screenshots.shutil, "which", lambda _name: "/usr/bin/npx")
    monkeypatch.setattr(screenshots.subprocess, "run", lambda command, **_k:
                        subprocess.CompletedProcess(command, 1, "", "net::ERR_CONNECTION_REFUSED"))
    with pytest.raises(ScreenshotError, match="ERR_CONNECTION_REFUSED"):
        capture("http://localhost:1", parse_screens(["/"]), tmp_path)

    def timeout(command, **_k):
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(screenshots.subprocess, "run", timeout)
    with pytest.raises(ScreenshotError, match="timed out"):
        capture("http://localhost:1", parse_screens(["/"]), tmp_path)


def test_neither_tool_says_how_to_install(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _no_playwright(monkeypatch)
    monkeypatch.setattr(screenshots.shutil, "which", lambda _name: None)

    with pytest.raises(ScreenshotError, match="playwright install chromium"):
        capture("http://localhost:8000", parse_screens(["/"]), tmp_path)


def test_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen = {}

    def fake_capture(base_url, screens, out_dir, size, wait_ms):
        seen.update(base_url=base_url, size=size, wait_ms=wait_ms)
        return [out_dir / f"{s.name}.png" for s in screens]

    monkeypatch.setattr("kingmadoc.cli.capture", fake_capture)
    out = tmp_path / "img"

    result = CliRunner().invoke(cli, ["screenshots", "http://localhost:8000", "/c=screen-us-1",
                                      "-o", str(out), "--size", "800x600", "--wait", "0"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == str(out / "screen-us-1.png")
    assert seen == {"base_url": "http://localhost:8000", "size": (800, 600), "wait_ms": 0}
    bad = CliRunner().invoke(cli, ["screenshots", "http://x", "/", "--size", "big"])
    assert bad.exit_code == 2
    monkeypatch.undo()
    error = CliRunner().invoke(cli, ["screenshots", "ftp://x", "/"])
    assert error.exit_code == 1 and "http(s)" in error.output
