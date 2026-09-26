"""File naming helpers shared by all commands (pure)."""

from __future__ import annotations

import hashlib
import re
import unicodedata

# Slugs become file names; keep them short enough to read in a directory listing.
MAX_SLUG_LENGTH = 40
# Hex digits of the fallback hash for untransliterable text: short, collisions unlikely.
HASH_LENGTH = 8


def slugify(text: str, max_length: int = MAX_SLUG_LENGTH) -> str:
    """Convert text to a kebab-case slug of at most ``max_length`` characters.

    Args:
        text: Any string.
        max_length: Maximum slug length; longer slugs are cut at a word boundary.

    Accented letters are transliterated (``é`` -> ``e``). If the text has letters or
    digits but none survive (e.g. Cyrillic or Chinese), the slug is ``feature-`` plus a
    short hash of the text, so different descriptions never share a file name. Text
    without any letters or digits becomes ``feature``.

    Returns:
        Lowercase, hyphen-separated ASCII slug.

    Example:
        >>> slugify("Add OAuth2 login (Google & GitHub)!")
        'add-oauth2-login-google-github'
        >>> slugify("Café crème")
        'cafe-creme'
    """
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    if not slug and any(char.isalnum() for char in text):
        digest = hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()
        return f"feature-{digest[:HASH_LENGTH]}"
    if len(slug) > max_length:
        cut = slug[:max_length]
        # Drop a partial last word, unless the slug is a single long word.
        if slug[max_length] != "-" and "-" in cut:
            cut = cut.rsplit("-", 1)[0]
        slug = cut.strip("-")
    return slug or "feature"
