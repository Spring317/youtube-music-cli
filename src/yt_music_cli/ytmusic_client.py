"""YTMusic API client factory.

Single Responsibility: creates and validates the YTMusic connection.
Everything else receives a ready-to-use ``YTMusic`` instance; nothing
else knows how it was initialised.
"""

from __future__ import annotations

import sys

from ytmusicapi import YTMusic

from .ui import error


def get_ytmusic() -> YTMusic:
    """Initialise and return an unauthenticated :class:`YTMusic` instance.

    Unauthenticated access is sufficient for searching, browsing albums,
    and fetching public playlists.  Exits the process on failure.
    """
    try:
        return YTMusic()
    except Exception as exc:
        error(f"Could not initialise YTMusic: {exc}")
        sys.exit(1)
