"""YouTube Music URL parsing.

Single Responsibility: pure string/regex logic to recognise and decode
YTMusic / YouTube URLs.  No network calls, no I/O.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

from .models import ParsedUrl

_YTM_HOST_RE = re.compile(
    r"(music\.youtube\.com|youtube\.com|youtu\.be)", re.IGNORECASE
)


def is_url(text: str) -> bool:
    """Return ``True`` if *text* looks like a YouTube/YTMusic URL."""
    return (
        text.startswith(("http://", "https://", "www."))
        or _YTM_HOST_RE.search(text) is not None
    )


def parse_ytm_url(url: str) -> ParsedUrl:
    """Parse a YouTube Music / YouTube URL into a :class:`ParsedUrl`.

    The ``type`` field will be one of:
    ``"album_browse"``, ``"album_olak"``, ``"playlist"``,
    ``"video"``, or ``"unknown"``.

    Supported patterns
    ------------------
    * Album browse: ``/browse/MPREb_…``
    * Album OLAK5:  ``?list=OLAK5uy_…``
    * Playlist:     ``?list=PL…``
    * Video:        ``?v=…``
    """
    parsed = urlparse(url)
    qs     = parse_qs(parsed.query)
    path   = parsed.path

    if "/browse/" in path:
        browse_id = path.split("/browse/")[-1].split("?")[0].strip("/")
        if browse_id.startswith("MPREb_"):
            return ParsedUrl(type="album_browse", id=browse_id)

    if "list" in qs:
        list_id = qs["list"][0]
        if list_id.startswith("OLAK5uy_"):
            return ParsedUrl(type="album_olak", id=list_id)
        return ParsedUrl(type="playlist", id=list_id)

    if "v" in qs:
        return ParsedUrl(type="video", id=qs["v"][0])

    return ParsedUrl(type="unknown", id="")
