"""Shared data model definitions.

All TypedDicts use the two-class inheritance pattern
(required base + optional subclass with ``total=False``) for Python ≥3.10
compatibility without needing ``typing_extensions``.

Single Responsibility: pure data shapes – no logic, no I/O.
"""

from typing import TypedDict


# ── Track ─────────────────────────────────────────────────────────────────────

class _TrackRequired(TypedDict):
    videoId: str
    title: str
    artists: str    # pre-formatted display string, e.g. "Artist A, Artist B"
    duration: str


class Track(_TrackRequired, total=False):
    """A single playable track as stored inside a :class:`SavedToken`."""
    isAvailable: bool
    localFile: str  # absolute path to a downloaded audio file


# ── SavedToken ────────────────────────────────────────────────────────────────

class _SavedTokenRequired(TypedDict):
    kind: str       # "album" | "playlist"
    title: str
    author: str
    browseId: str
    playlistId: str
    savedAt: str    # human-readable, e.g. "2026-04-06 23:00"
    tracks: list[Track]


class SavedToken(_SavedTokenRequired, total=False):
    """Persisted metadata for a saved album or playlist."""
    offline: bool
    localDir: str
    _path: str      # injected at runtime; NEVER written to disk


# ── ParsedUrl ─────────────────────────────────────────────────────────────────

class ParsedUrl(TypedDict):
    """Result produced by :func:`url_parser.parse_ytm_url`."""
    type: str   # "album_browse" | "album_olak" | "playlist" | "video" | "unknown"
    id: str
