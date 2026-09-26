"""Find or install the D2 binary used by ``kingmadoc render`` (so pip install is enough).

Order: ``KINGMADOC_D2``, a ``d2`` on ``PATH``, a previously downloaded copy, and finally
a one-time download of the pinned D2 release from GitHub into the user cache. The
download is checked against the SHA-256 pinned below before anything is installed; set
``KINGMADOC_D2_DOWNLOAD=0`` to never download.

D2 is licensed under MPL-2.0; its licence file is installed next to the binary.
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType

from kingmadoc.exceptions import RenderError

D2_VERSION = "v0.9.0"
D2_RELEASE_URL = "https://github.com/d2lang/d2/releases/download/" + D2_VERSION + "/{asset}"
# (sys.platform, normalized machine) -> (release asset, SHA-256). Checked against the
# release's SHA256SUMS and GitHub's asset digests when pinned.
D2_ASSETS: Mapping[tuple[str, str], tuple[str, str]] = MappingProxyType({
    ("linux", "amd64"): (
        "d2-v0.9.0-linux-amd64.tar.gz",
        "5669ddc46b99e942cc96078f4a4e36d5e62103348f4c05179ede27802fdd87a9",
    ),
    ("linux", "arm64"): (
        "d2-v0.9.0-linux-arm64.tar.gz",
        "ac2c028697199479acb321db1e3d68caee9f2ba492ed73caa3cd13f3829bf913",
    ),
    ("darwin", "amd64"): (
        "d2-v0.9.0-macos-amd64.tar.gz",
        "cad39576a480d6bb02ea142fef1726647914b0d2da51ccc9b30b660a2b1babf0",
    ),
    ("darwin", "arm64"): (
        "d2-v0.9.0-macos-arm64.tar.gz",
        "eaf6c0c143e56dd9fa97bfb6df25ea9c1ebce40245f056a0768cf1a6c15d3064",
    ),
    ("win32", "amd64"): (
        "d2-v0.9.0-windows-amd64.tar.gz",
        "5f63b643de8f5a6dfb922d172e1b5496e4caf47497c33c4427cf1127f28c340f",
    ),
    ("win32", "arm64"): (
        "d2-v0.9.0-windows-arm64.tar.gz",
        "dd05cab459410c287d7ca3eb9cf78145a071742ee8e1b81a0122f84f471883e1",
    ),
})
# Seconds for the whole download (about 18 MB).
DOWNLOAD_TIMEOUT = 120

_MANUAL = (
    "Install D2 yourself from https://d2lang.com/tour/install (a single binary), "
    "or set KINGMADOC_D2 to its path."
)


def ensure_d2(notify: Callable[[str], None]) -> list[str]:
    """Return the command that runs D2, downloading the pinned release if needed.

    Args:
        notify: Called with a progress message before a download (e.g. print to stderr).

    Returns:
        ``[path to d2]``.

    Raises:
        RenderError: If D2 is not available and cannot (or may not) be downloaded.
    """
    configured = os.environ.get("KINGMADOC_D2")
    if configured:
        return [configured]
    installed = shutil.which("d2")
    if installed:
        return [installed]
    binary = _cache_dir() / "d2" / D2_VERSION / _executable()
    if binary.is_file():
        return [str(binary)]
    if os.environ.get("KINGMADOC_D2_DOWNLOAD", "").lower() in {"0", "false", "no"}:
        raise RenderError(f"D2 is not installed and downloading is off. {_MANUAL}")
    asset = _platform_asset()
    if asset is None:
        raise RenderError(
            f"There is no D2 release for this platform ({sys.platform}, "
            f"{platform.machine()}). {_MANUAL}"
        )
    notify(f"Downloading D2 {D2_VERSION} (about 18 MB, once) to render diagrams…")
    _install(*asset, binary)
    return [str(binary)]


def _install(asset: str, sha256: str, binary: Path) -> None:
    """Download, verify and unpack the release; nothing is installed unless it matches."""
    binary.parent.mkdir(parents=True, exist_ok=True)
    url = D2_RELEASE_URL.format(asset=asset)
    with tempfile.TemporaryDirectory(dir=binary.parent) as tmp:
        archive = Path(tmp) / asset
        try:
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response:
                archive.write_bytes(response.read())
        except (urllib.error.URLError, OSError) as exc:
            raise RenderError(f"Could not download D2 from {url}: {exc}. {_MANUAL}") from exc
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != sha256:
            raise RenderError(
                f"The D2 download does not match its pinned checksum "
                f"(expected {sha256}, got {actual}); nothing was installed. {_MANUAL}"
            )
        root = f"d2-{D2_VERSION}"
        with tarfile.open(archive) as tar:
            # Only these two members are read, by exact name: no path in the archive can
            # write outside the cache.
            members = {
                f"{root}/bin/{_executable()}": binary.name,
                f"{root}/LICENSE.txt": "LICENSE.txt",
            }
            for member, target in members.items():
                source = tar.extractfile(member)
                if source is None:
                    raise RenderError(f"Unexpected D2 archive layout: {member} missing")
                (Path(tmp) / target).write_bytes(source.read())
        (Path(tmp) / binary.name).chmod(0o755)
        try:
            os.replace(Path(tmp) / "LICENSE.txt", binary.parent / "LICENSE.txt")
            os.replace(Path(tmp) / binary.name, binary)
        except OSError as exc:
            # Another kingmadoc process may have installed (and be running) it meanwhile;
            # on Windows a running .exe cannot be replaced.
            if not binary.is_file():
                raise RenderError(f"Could not install D2 to {binary}: {exc}") from exc


def _platform_asset() -> tuple[str, str] | None:
    machine = platform.machine().lower()
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
    return D2_ASSETS.get((sys.platform, arch.get(machine, machine)))


def _executable() -> str:
    return "d2.exe" if sys.platform == "win32" else "d2"


def _cache_dir() -> Path:
    """The user cache directory (``KINGMADOC_CACHE_DIR`` overrides it) + ``kingmadoc``."""
    override = os.environ.get("KINGMADOC_CACHE_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return base / "kingmadoc"
