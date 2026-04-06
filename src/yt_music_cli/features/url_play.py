"""Feature: Play content directly from a YouTube Music URL.

Single Responsibility: parses a URL and delegates to the correct handler
(album or playlist).  Contains no playback or search logic itself.
"""

from __future__ import annotations

from ytmusicapi import YTMusic

from ..ui import c, error, info, CYAN
from ..url_parser import parse_ytm_url
from ..player import play_track
from .albums import play_album_by_browse_id
from .playlists import play_playlist_from_id


def feature_play_from_url(ytm: YTMusic) -> None:
    """Prompt for a YouTube Music URL and dispatch to the right handler."""
    url = input(c("\n  🔗 Paste a YouTube Music URL: ", CYAN, bold=True)).strip()
    if not url:
        return

    parsed = parse_ytm_url(url)
    kind   = parsed["type"]
    pid    = parsed["id"]

    if kind == "album_browse":
        play_album_by_browse_id(ytm, pid)

    elif kind == "album_olak":
        info(f"Resolving album from playlist ID {pid}…")
        try:
            browse_id = ytm.get_album_browse_id(pid)
        except Exception as exc:
            error(f"Could not resolve album: {exc}")
            return
        if not browse_id:
            error("Could not resolve album browseId from that link.")
            return
        play_album_by_browse_id(ytm, browse_id)

    elif kind == "playlist":
        play_playlist_from_id(ytm, pid)

    elif kind == "video":
        info(f"Detected video ID: {pid}")
        play_track(pid, "Direct link", "—")

    else:
        error(
            "Unrecognised URL format.  Supported: album browse links, "
            "playlist links, OLAK5 links, video links."
        )
