"""Screenshots of a running app for explainers (``kingmadoc screenshots``).

One browser for every screen when the optional Playwright package is installed
(``pip install 'kingmadoc[screenshots]'`` and ``playwright install chromium``);
otherwise one ``npx playwright screenshot`` per screen (Node.js). Only ``http`` and
``https`` URLs; the files land in the given folder, named after the screen.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404 - runs npx with a fixed argument list, no shell
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

from kingmadoc.exceptions import ScreenshotError
from kingmadoc.naming import slugify

DEFAULT_SIZE = (1280, 800)
# How long a page may take to settle, in milliseconds.
DEFAULT_WAIT_MS = 1500
NPX_TIMEOUT = 180


@dataclass(frozen=True)
class Screen:
    """One screen to capture: a path on the app and the image name (without .png)."""

    route: str
    name: str


def parse_screens(items: Sequence[str]) -> list[Screen]:
    """``/contact=screen-us-1`` or ``/contact`` (named after the route) per screen.

    Raises:
        ScreenshotError: If no screens are given or a name is empty.
    """
    screens = []
    for item in items:
        route, _, name = item.partition("=")
        name = slugify(name or route.strip("/") or "home")
        if not route.strip() or not name:
            raise ScreenshotError(f"Cannot read screen {item!r}; use ROUTE=NAME")
        screens.append(Screen(route.strip(), name))
    if not screens:
        raise ScreenshotError("Name at least one screen, e.g. /contact=screen-us-1")
    return screens


def screen_url(base_url: str, route: str) -> str:
    """The full URL of a screen; only http(s).

    Raises:
        ScreenshotError: For another scheme or a URL without a host.
    """
    url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ScreenshotError(f"Only http(s) URLs can be captured, not {url!r}")
    return url


def capture(
    base_url: str,
    screens: Sequence[Screen],
    out_dir: Path,
    size: tuple[int, int] = DEFAULT_SIZE,
    wait_ms: int = DEFAULT_WAIT_MS,
) -> list[Path]:
    """Capture every screen as ``<out_dir>/<name>.png`` and return the paths.

    Raises:
        ScreenshotError: If neither Playwright nor npx is available, or a capture fails.
    """
    targets = [(screen_url(base_url, s.route), out_dir / f"{s.name}.png") for s in screens]
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import (  # type: ignore[import-not-found]  # optional extra
            Error as PlaywrightError,
        )
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _capture_with_npx(targets, size, wait_ms)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": size[0], "height": size[1]})
            for url, path in targets:
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(wait_ms)
                page.screenshot(path=str(path))
            browser.close()
    except PlaywrightError as exc:
        raise ScreenshotError(f"Playwright could not capture the screens: {exc}") from exc
    return [path for _, path in targets]


def _capture_with_npx(
    targets: Sequence[tuple[str, Path]], size: tuple[int, int], wait_ms: int
) -> list[Path]:
    npx = shutil.which("npx")
    if npx is None:
        raise ScreenshotError(
            "Neither Playwright nor npx is available. Install one: "
            "pipx inject kingmadoc playwright && playwright install chromium, "
            "or Node.js (for npx playwright)."
        )
    for url, path in targets:
        command = [npx, "-y", "playwright", "screenshot",
                   f"--viewport-size={size[0]},{size[1]}", f"--wait-for-timeout={wait_ms}",
                   url, str(path)]
        try:
            done = subprocess.run(  # noqa: S603 - fixed arguments, URL checked above
                command, capture_output=True, text=True, timeout=NPX_TIMEOUT, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise ScreenshotError(f"npx playwright timed out on {url}") from exc
        if done.returncode != 0 or not path.is_file():
            detail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no output"]
            raise ScreenshotError(f"npx playwright could not capture {url}: {detail[0]}")
    return [path for _, path in targets]
