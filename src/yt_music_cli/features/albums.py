"""Feature: Search & play albums.

Exposes two public callables:

* :func:`play_album_by_browse_id` – used both here and by the URL-play
  feature (Open/Closed: reusable without modification).
* :func:`feature_search_album` – main-menu entry point.
"""

from __future__ import annotations

from ytmusicapi import YTMusic

from ..ui import (
    c, divider, warn, error, info, pick, success,
    BOLD, WHITE, YELLOW, GREY, CYAN, MAGENTA, GREEN, RED, DIM,
)
from ..search import search_albums, fmt_artists
from ..player import play_track
from ..library import save_token, download_offline


# ── Shared playback helpers ───────────────────────────────────────────────────

def _play_all(tracks: list[dict], title: str) -> None:
    from ..player import play_playlist
    available_tracks = []
    for i, t in enumerate(tracks, 1):
        if not t.get("isAvailable", True):
            warn(f"Track {i} ({t.get('title', '?')}) unavailable, skipping.")
        else:
            available_tracks.append(t)
            
    play_playlist(available_tracks, title)


def _pick_track(tracks: list[dict]) -> None:
    available = [
        (i, t) for i, t in enumerate(tracks, 1)
        if t.get("isAvailable", True) and t.get("videoId")
    ]
    if not available:
        warn("No available tracks to pick.")
        return

    def label(item: tuple[int, dict]) -> str:
        i, t = item
        return (
            c(f"{i:>2}.", DIM + GREY)
            + f" {c(t.get('title', '?'), WHITE)}"
            + c(f" – {fmt_artists(t.get('artists'))}", GREY)
        )

    idx = pick("Pick a track", available, label)
    if idx is None:
        return
    _, t = available[idx]
    play_track(t["videoId"], t.get("title", "?"), fmt_artists(t.get("artists")))


# ── Public API ────────────────────────────────────────────────────────────────

def play_album_by_browse_id(
    ytm: YTMusic,
    browse_id: str,
    album_title: str = "",
) -> None:
    """Fetch an album by YTMusic *browse_id* and present play / save options."""
    info("Fetching album tracks…")
    try:
        album = ytm.get_album(browse_id)
    except Exception as exc:
        error(f"Could not fetch album: {exc}")
        return

    title  = album.get("title", album_title or "Unknown Album")
    artist = fmt_artists(album.get("artists"))
    year   = album.get("year", "")
    tracks: list[dict] = album.get("tracks", [])

    if not tracks:
        warn("No tracks found in this album.")
        return

    print()
    divider("═")
    print(c(f"  💿  {title}", MAGENTA, bold=True))
    print(c(f"       {artist}  {year}", GREY))
    print(c(f"       {len(tracks)} tracks", DIM + CYAN))
    divider("═")

    for i, t in enumerate(tracks, 1):
        avail_str = "" if t.get("isAvailable", True) else c(" [unavailable]", RED)
        print(
            c(f"  {i:>2}.", DIM + GREY)
            + f" {c(t.get('title', '?'), WHITE)}"
            + c(f" – {fmt_artists(t.get('artists'))}", GREY)
            + c(f"  {t.get('duration', '')}", DIM + GREY)
            + avail_str
        )

    divider()
    print(c(
        "  [A] Play all   [P] Pick a track   "
        "[S] Save token   [D] Download offline   [0] Back",
        CYAN,
    ))
    choice = input(c("\n  Your choice: ", MAGENTA, bold=True)).strip().upper()

    if choice == "A":
        _play_all(tracks, title)
    elif choice == "P":
        _pick_track(tracks)
    elif choice == "S":
        save_token(kind="album", title=title, author=artist,
                   browse_id=browse_id, tracks=tracks)
    elif choice == "D":
        download_offline(kind="album", title=title, author=artist,
                         browse_id=browse_id, tracks=tracks)


def feature_search_album(ytm: YTMusic) -> None:
    """Search for albums and let the user choose one to play."""
    query = input(c("\n  🔍 Search albums: ", CYAN, bold=True)).strip()
    if not query:
        return

    info(f"Searching albums for '{query}'...")
    results = search_albums(ytm, query)
    if not results:
        warn("No albums found.")
        return

    divider()
    print(c("  Search Results – Albums", BOLD + WHITE))
    divider(char="·")

    def label(a: dict) -> str:
        return (
            f"{c(a.get('title', '?'), WHITE, bold=True)} "
            f"{c('by', DIM + GREY)} "
            f"{c(fmt_artists(a.get('artists')), YELLOW)}  "
            f"{c(a.get('year', ''), DIM + GREY)}"
        )

    idx = pick("Pick an album", results, label)
    if idx is None:
        return

    album  = results[idx]
    browse = album.get("browseId")
    if not browse:
        error("No browseId for this album.")
        return

    play_album_by_browse_id(ytm, browse, album.get("title", ""))
