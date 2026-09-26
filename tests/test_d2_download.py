"""Tests for the automatic D2 download: `kingmadoc render` needs nothing but pip install."""

import hashlib
import io
import os
import sys
import tarfile
from pathlib import Path

import pytest

from kingmadoc import d2_binary
from kingmadoc.d2_binary import D2_VERSION, ensure_d2
from kingmadoc.exceptions import RenderError

EXE = "d2.exe" if os.name == "nt" else "d2"


def _archive(tmp_path: Path, content: bytes = b"fake d2 binary") -> Path:
    """A release archive laid out like D2's: d2-<version>/bin/d2 plus LICENSE.txt."""
    path = tmp_path / "release.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for name, data in ((f"d2-{D2_VERSION}/bin/{EXE}", content),
                           (f"d2-{D2_VERSION}/LICENSE.txt", b"MPL-2.0")):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


@pytest.fixture
def release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Serve a local archive as the release for this platform; isolate cache and PATH."""
    archive = _archive(tmp_path)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    monkeypatch.setattr(d2_binary, "_platform_asset", lambda: (archive.name, digest))
    monkeypatch.setattr(d2_binary, "D2_RELEASE_URL", archive.parent.as_uri() + "/{asset}")
    monkeypatch.setenv("KINGMADOC_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    monkeypatch.delenv("KINGMADOC_D2", raising=False)
    monkeypatch.delenv("KINGMADOC_D2_DOWNLOAD", raising=False)
    return archive


def test_downloads_verifies_and_caches(release: Path, tmp_path: Path) -> None:
    """First use downloads the pinned release, checks it, and installs it in the cache."""
    messages: list[str] = []

    command = ensure_d2(messages.append)

    binary = Path(command[0])
    assert binary == tmp_path / "cache" / "d2" / D2_VERSION / EXE
    assert binary.read_bytes() == b"fake d2 binary"
    assert (binary.parent / "LICENSE.txt").read_text() == "MPL-2.0"
    if os.name != "nt":
        assert os.access(binary, os.X_OK)
    assert any("Downloading D2" in m for m in messages)


def test_second_use_needs_no_download(release: Path) -> None:
    """Once cached, D2 works offline: the archive is not needed any more."""
    first = ensure_d2(lambda _m: None)
    release.unlink()

    assert ensure_d2(lambda _m: None) == first


def test_checksum_mismatch_installs_nothing(
    release: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A download that does not match the pinned SHA-256 is rejected."""
    monkeypatch.setattr(d2_binary, "_platform_asset", lambda: (release.name, "0" * 64))

    with pytest.raises(RenderError, match="checksum"):
        ensure_d2(lambda _m: None)

    assert not (tmp_path / "cache" / "d2" / D2_VERSION / EXE).exists()


def test_download_can_be_disabled(release: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KINGMADOC_D2_DOWNLOAD=0 never downloads and explains the manual route."""
    monkeypatch.setenv("KINGMADOC_D2_DOWNLOAD", "0")

    with pytest.raises(RenderError, match="d2lang.com"):
        ensure_d2(lambda _m: None)


def test_unsupported_platform(release: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Platforms without a D2 release get a clear message instead of a crash."""
    monkeypatch.setattr(d2_binary, "_platform_asset", lambda: None)

    with pytest.raises(RenderError, match="no D2 release for this platform"):
        ensure_d2(lambda _m: None)


def test_configured_or_installed_d2_is_preferred(
    release: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KINGMADOC_D2 wins, then a d2 on PATH; neither triggers a download."""
    monkeypatch.setenv("KINGMADOC_D2", "/opt/d2")
    assert ensure_d2(lambda _m: None) == ["/opt/d2"]

    monkeypatch.delenv("KINGMADOC_D2")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    own = bin_dir / EXE
    own.write_text("", encoding="utf-8")
    own.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    found = ensure_d2(lambda _m: None)
    # Windows returns the PATHEXT spelling (d2.EXE); its file names ignore case.
    assert [os.path.normcase(p) for p in found] == [os.path.normcase(str(own))]
    assert not (tmp_path / "cache").exists()


def test_every_supported_platform_has_a_pinned_checksum() -> None:
    """Each pinned asset has a 64-hex SHA-256 and the release naming scheme."""
    for (system, machine), (asset, digest) in d2_binary.D2_ASSETS.items():
        assert asset.startswith(f"d2-{D2_VERSION}-") and asset.endswith(".tar.gz"), asset
        assert len(digest) == 64 and int(digest, 16) >= 0, (system, machine)


@pytest.mark.skipif(
    os.environ.get("KINGMADOC_TEST_NETWORK") != "1", reason="set KINGMADOC_TEST_NETWORK=1"
)
def test_real_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Against the real GitHub release (opt-in, needs network)."""
    monkeypatch.setenv("KINGMADOC_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.delenv("KINGMADOC_D2", raising=False)

    binary = ensure_d2(lambda message: print(message, file=sys.stderr))

    assert Path(binary[0]).is_file()
