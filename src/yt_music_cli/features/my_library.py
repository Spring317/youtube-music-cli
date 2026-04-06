"""Feature: My Library — browse and play saved tokens and offline downloads.

Single Responsibility: presents the user's saved content, supports
playback of both streamed tokens and locally downloaded files, and allows
deletion of saved entries.
"""

from __future__ import annotations

from pathlib import Path

from ytmusicapi import YTMusic

from ..ui import (
    c, divider, warn, error, info, pick, success,
    BOLD, WHITE, GREY, CYAN, MAGENTA, GREEN, RED, DIM,
)
from ..models import SavedToken, Track
from ..player import play_track, play_local_file
from ..library import load_tokens


# ── Private helpers ───────────────────────────────────────────────────────────

def _play_all_token(tracks: list[Track], title: str) -> None:
    print(c(f"\n  ▶▶  Playing: {title}", GREEN, bold=True))
    for i, t in enumerate(tracks, 1):
        vid     = t.get("videoId", "")
        t_title = t.get("title", "?")
        t_art   = t.get("artists", "?")
        local   = t.get("localFile", "")
        try:
            if local and Path(local).exists():
                play_local_file(local, t_title, t_art, track_num=i, total=len(tracks))
            elif vid:
                play_track(vid, t_title, t_art, track_num=i, total=len(tracks))
            else:
                warn(f"Track {i} has no playable source, skipping.")
        except KeyboardInterrupt:
            print(c("\n  ⏹  Playback stopped.", YELLOW))
            return
    success(f"Finished: {title}")


def _pick_token_track(tracks: list[Track]) -> None:
    available = [
        (i, t) for i, t in enumerate(tracks, 1)
        if t.get("videoId") or (t.get("localFile") and Path(t.get("localFile", "")).exists())
    ]
    if not available:
        warn("No playable tracks found.")
        return

    def label(item: tuple[int, Track]) -> str:
        i, t = item
        local = t.get("localFile", "")
        offline_mark = c(" 💾", DIM + GREEN) if local and Path(local).exists() else ""
        return (
            c(f"{i:>2}.", DIM + GREY)
            + f" {c(t.get('title', '?'), WHITE)}"
            + c(f" – {t.get('artists', '?')}", GREY)
            + offline_mark
        )

    idx = pick("Pick a track", available, label)
    if idx is None:
        return

    _, t = available[idx]
    local = t.get("localFile", "")
    if local and Path(local).exists():
        play_local_file(local, t.get("title", "?"), t.get("artists", "?"))
    elif t.get("videoId"):
        play_track(t["videoId"], t.get("title", "?"), t.get("artists", "?"))
    else:
        error("No playable source for this track.")


def _play_token(token: SavedToken) -> None:
    """Display a saved token and offer play / delete actions."""
    title      = token.get("title", "?")
    author     = token.get("author", "?")
    is_offline = token.get("offline", False)
    tracks: list[Track] = token.get("tracks", [])

    if not tracks:
        warn("No tracks in this saved item.")
        return

    print()
    divider("═")
    icon = "💾" if is_offline else "🔖"
    print(c(f"  {icon}  {title}", MAGENTA, bold=True))
    print(c(f"       by {author}", GREY))
    mode_str = c("  Offline 💾", DIM + GREEN) if is_offline else c("  Streaming 🌐", DIM + CYAN)
    print(mode_str)
    print(c(f"       {len(tracks)} tracks", DIM + CYAN))
    divider("═")

    for i, t in enumerate(tracks, 1):
        avail_str  = "" if t.get("isAvailable", True) else c(" [unavailable]", RED)
        local      = t.get("localFile", "")
        local_str  = c(" 💾", DIM + GREEN) if local and Path(local).exists() else ""
        print(
            c(f"  {i:>2}.", DIM + GREY)
            + f" {c(t.get('title', '?'), WHITE)}"
            + c(f" – {t.get('artists', '?')}", GREY)
            + c(f"  {t.get('duration', '')}", DIM + GREY)
            + avail_str + local_str
        )

    divider()
    print(c("  [A] Play all   [P] Pick a track   [X] Delete saved   [0] Back", CYAN))
    choice = input(c("\n  Your choice: ", MAGENTA, bold=True)).strip().upper()

    if choice == "A":
        _play_all_token(tracks, title)
    elif choice == "P":
        _pick_token_track(tracks)
    elif choice == "X":
        path = token.get("_path", "")
        if path and Path(path).exists():
            confirm = input(c(f"\n  Delete '{title}'? [y/N]: ", RED, bold=True)).strip().lower()
            if confirm == "y":
                Path(path).unlink()
                success(f"Deleted: {path}")
                info("Downloaded audio files (if any) are NOT deleted.")
            else:
                info("Cancelled.")
        else:
            error("Token file not found.")


# ── Public API ────────────────────────────────────────────────────────────────

def feature_my_library(_ytm: YTMusic) -> None:
    """Show the user's saved playlists / albums and play from them."""
    tokens = load_tokens()

    if not tokens:
        print()
        divider()
        print(c("  📚  My Library", BOLD + WHITE))
        divider(char="·")
        warn("No saved items yet.")
        info("Save an album or playlist with [S] or [D] when viewing one.")
        divider()
        return

    while True:
        tokens = load_tokens()
        if not tokens:
            warn("Library is now empty.")
            return

        print()
        divider("═")
        print(c("  📚  My Library", BOLD + WHITE))
        divider(char="·")

        def label(tok: SavedToken) -> str:
            kind    = tok.get("kind", "?")
            title   = tok.get("title", "?")
            author  = tok.get("author", "?")
            n       = len(tok.get("tracks", []))
            saved   = tok.get("savedAt", "")
            icon    = "💿" if kind == "album" else "📋"
            mode    = c("  💾 Offline", DIM + GREEN) if tok.get("offline") else c("  🌐 Token", DIM + CYAN)
            return (
                f"{icon}  {c(title, WHITE, bold=True)}"
                + c(f" by {author}", GREY)
                + c(f"  {n} tracks", DIM + CYAN)
                + mode
                + c(f"  {saved}", DIM + GREY)
            )

        idx = pick("Pick an item", tokens, label)
        if idx is None:
            return
        _play_token(tokens[idx])
