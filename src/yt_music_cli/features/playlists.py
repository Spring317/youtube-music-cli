"""Feature: Search & play playlists.

Exposes two public callables:

* :func:`play_playlist_from_id` – reused by the URL-play feature.
* :func:`feature_search_playlist` – main-menu entry point.
"""

from __future__ import annotations

from ytmusicapi import YTMusic

from ..ui import (
    c, divider, warn, error, info, pick, success,
    BOLD, WHITE, YELLOW, GREY, CYAN, MAGENTA, GREEN, DIM,
)
from ..search import search_playlists, fmt_artists
from ..player import play_track
from ..library import save_token, download_offline


# ── Private helpers ───────────────────────────────────────────────────────────

def _play_all(tracks: list[dict], title: str) -> None:
    print(c(f"\n  ▶▶  Playing full playlist: {title}", GREEN, bold=True))
    for i, t in enumerate(tracks, 1):
        vid = t.get("videoId")
        if not vid:
            warn(f"Track {i} has no video ID, skipping.")
            continue
        try:
            play_track(
                vid,
                t.get("title", "?"),
                fmt_artists(t.get("artists")),
                track_num=i,
                total=len(tracks),
            )
        except KeyboardInterrupt:
            print(c("\n  ⏹  Playlist playback stopped.", YELLOW))
            return
    success("Playlist finished!")


def _pick_track(tracks: list[dict]) -> None:
    available = [(i, t) for i, t in enumerate(tracks, 1) if t.get("videoId")]

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

def play_playlist_from_id(
    ytm: YTMusic,
    playlist_id: str,
    name: str = "",
) -> None:
    """Fetch a playlist by *playlist_id* and present play / save options."""
    info("Fetching playlist…")
    try:
        pl = ytm.get_playlist(playlist_id, limit=None)
    except Exception as exc:
        error(f"Could not fetch playlist: {exc}")
        return

    pl_title  = pl.get("title", name or "Unknown Playlist")
    pl_author = pl.get("author", {})
    if isinstance(pl_author, dict):
        pl_author = pl_author.get("name", "Unknown")
    tracks: list[dict] = pl.get("tracks", [])

    print()
    divider("═")
    print(c(f"  📋  {pl_title}", MAGENTA, bold=True))
    print(c(f"       by {pl_author}", GREY))
    print(c(f"       {len(tracks)} tracks", DIM + CYAN))
    divider("═")

    for i, t in enumerate(tracks, 1):
        print(
            c(f"  {i:>2}.", DIM + GREY)
            + f" {c(t.get('title', '?'), WHITE)}"
            + c(f" – {fmt_artists(t.get('artists'))}", GREY)
            + c(f"  {t.get('duration', '')}", DIM + GREY)
        )

    divider()
    print(c(
        "  [A] Play all   [P] Pick a track   "
        "[S] Save token   [D] Download offline   [0] Back",
        CYAN,
    ))
    choice = input(c("\n  Your choice: ", MAGENTA, bold=True)).strip().upper()

    if choice == "A":
        _play_all(tracks, pl_title)
    elif choice == "P":
        _pick_track(tracks)
    elif choice == "S":
        save_token(kind="playlist", title=pl_title, author=pl_author,
                   playlist_id=playlist_id, tracks=tracks)
    elif choice == "D":
        download_offline(kind="playlist", title=pl_title, author=pl_author,
                         playlist_id=playlist_id, tracks=tracks)


def feature_search_playlist(ytm: YTMusic) -> None:
    """Search for playlists and let the user choose one to play."""
    query = input(c("\n  🔍 Search playlists: ", CYAN, bold=True)).strip()
    if not query:
        return

    info(f"Searching playlists for '{query}'...")
    results = search_playlists(ytm, query)
    if not results:
        warn("No playlists found.")
        return

    divider()
    print(c("  Search Results – Playlists", BOLD + WHITE))
    divider(char="·")

    def label(p: dict) -> str:
        author = p.get("author", "?")
        if isinstance(author, list) and author:
            author = author[0].get("name", "?")
        return (
            f"{c(p.get('title', '?'), WHITE, bold=True)} "
            f"{c('by', DIM + GREY)} {c(str(author), YELLOW)}  "
            f"{c(str(p.get('itemCount', '?')) + ' tracks', DIM + GREY)}"
        )

    idx = pick("Pick a playlist", results, label)
    if idx is None:
        return

    pl    = results[idx]
    pl_id = pl.get("playlistId")
    if not pl_id:
        error("No playlistId found.")
        return

    play_playlist_from_id(ytm, pl_id, pl.get("title", ""))
