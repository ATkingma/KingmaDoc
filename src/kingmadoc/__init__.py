"""KingmaDoc: feature documentation for AI coding agents."""

from importlib import metadata

try:
    # Set at build time from the git tag (hatch-vcs), see pyproject.toml.
    __version__ = metadata.version("kingmadoc")
except metadata.PackageNotFoundError:  # a source tree that was never installed
    __version__ = "0+unknown"

__all__ = ["__version__"]
