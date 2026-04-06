"""Feature: Search & play a single song.

Single Responsibility: handles the "search → pick → play" workflow for
individual songs.  Delegates searching to :mod:`search` and playback
to :mod:`player`.
"""

from __future__ import annotations

from ytmusicapi import YTMusic

from ..ui import c, divider, warn, error, info, pick, BOLD, WHITE, YELLOW, GREY, CYAN, DIM
from ..search import search_songs, fmt_artists
from ..player import play_track


def feature_search_song(ytm: YTMusic) -> None:
    """Prompt for a query, display results, and play the chosen song."""
    query = input(c("\n  🔍 Search songs: ", CYAN, bold=True)).strip()
    if not query:
        return

    info(f"Searching songs for '{query}'...")
    results = search_songs(ytm, query)
    if not results:
        warn("No songs found.")
        return

    divider()
    print(c("  Search Results – Songs", BOLD + WHITE))
    divider(char="·")

    def label(s: dict) -> str:
        title   = s.get("title", "?")
        artists = fmt_artists(s.get("artists"))
        dur     = s.get("duration", "")
        return (
            f"{c(title, WHITE, bold=True)} {c('by', DIM + GREY)} "
            f"{c(artists, YELLOW)}  {c(dur, DIM + GREY)}"
        )

    idx = pick("Pick a song to play", results, label)
    if idx is None:
        return

    song    = results[idx]
    vid     = song.get("videoId")
    title   = song.get("title", "?")
    artists = fmt_artists(song.get("artists"))

    if not vid:
        error("No video ID found for this song.")
        return

    play_track(vid, title, artists)
