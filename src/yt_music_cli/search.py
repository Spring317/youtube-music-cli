"""YouTube Music search helpers and result formatting.

Single Responsibility: talks to the YTMusic API (search only) and
formats raw API responses into display-ready strings.
No playback, no persistence.
"""

from __future__ import annotations

from ytmusicapi import YTMusic


def fmt_artists(artists_list: list | None) -> str:
    """Convert a ytmusicapi artist list to a comma-separated display string.

    Handles both ``[{"name": "…"}, …]`` dicts and plain string lists.
    Returns ``"Unknown"`` for empty / ``None`` input.
    """
    if not artists_list:
        return "Unknown"
    return ", ".join(
        a.get("name", "") if isinstance(a, dict) else str(a)
        for a in artists_list
    )


def search_songs(ytm: YTMusic, query: str, limit: int = 8) -> list[dict]:
    """Search for songs and return up to *limit* results."""
    return ytm.search(query, filter="songs", limit=limit)  # type: ignore[return-value]


def search_albums(ytm: YTMusic, query: str, limit: int = 6) -> list[dict]:
    """Search for albums and return up to *limit* results."""
    return ytm.search(query, filter="albums", limit=limit)  # type: ignore[return-value]


def search_playlists(ytm: YTMusic, query: str, limit: int = 6) -> list[dict]:
    """Search for playlists and return up to *limit* results."""
    return ytm.search(query, filter="playlists", limit=limit)  # type: ignore[return-value]
