"""File naming helpers shared by all commands (pure)."""

from __future__ import annotations

import re

# Slugs become file names; keep them short enough to read in a directory listing.
MAX_SLUG_LENGTH = 40


def slugify(text: str, max_length: int = MAX_SLUG_LENGTH) -> str:
    """Convert text to a kebab-case slug of at most ``max_length`` characters.

    Args:
        text: Any string.
        max_length: Maximum slug length; longer slugs are cut at a word boundary.

    Returns:
        Lowercase, hyphen-separated slug (``"feature"`` if nothing remains).

    Example:
        >>> slugify("Add OAuth2 login (Google & GitHub)!")
        'add-oauth2-login-google-github'
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(slug) > max_length:
        cut = slug[:max_length]
        # Drop a partial last word, unless the slug is a single long word.
        if slug[max_length] != "-" and "-" in cut:
            cut = cut.rsplit("-", 1)[0]
        slug = cut.strip("-")
    return slug or "feature"
