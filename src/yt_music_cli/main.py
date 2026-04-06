#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════╗
║     🎵  YouTube Music CLI Player  🎵     ║
║         Powered by ytmusicapi             ║
╚═══════════════════════════════════════════╝
"""

import re
import subprocess
import sys
import time
from urllib.parse import urlparse, parse_qs

import yt_dlp
from ytmusicapi import YTMusic

# ─────────────────────────────────────────────────────────────
#  Terminal colour / formatting helpers (no external deps)
# ─────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

# Colours
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
GREY    = "\033[90m"

def c(text: str, colour: str, bold: bool = False) -> str:
    """Wrap text in ANSI colour codes."""
    prefix = BOLD if bold else ""
    return f"{prefix}{colour}{text}{RESET}"

def header():
    print(c("""
╔══════════════════════════════════════════════════╗
║   🎵   YouTube Music CLI Player  v2.0   🎵      ║
║        Powered by ytmusicapi + yt-dlp            ║
╚══════════════════════════════════════════════════╝""", CYAN, bold=True))

def divider(char: str = "─", width: int = 52, colour: str = GREY) -> None:
    print(c(char * width, colour))

def success(msg: str) -> None:
    print(c(f"  ✔  {msg}", GREEN))

def warn(msg: str) -> None:
    print(c(f"  ⚠  {msg}", YELLOW))

def error(msg: str) -> None:
    print(c(f"  ✖  {msg}", RED))

def info(msg: str) -> None:
    print(c(f"  ℹ  {msg}", CYAN))


# ─────────────────────────────────────────────────────────────
#  ytmusicapi initialisation (no auth – unauthenticated works
#  fine for searching, browsing albums and public playlists)
# ─────────────────────────────────────────────────────────────

def get_ytmusic() -> YTMusic:
    try:
        return YTMusic()
    except Exception as exc:
        error(f"Could not initialise YTMusic: {exc}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
#  URL helpers
# ─────────────────────────────────────────────────────────────

YTM_HOST_RE = re.compile(r"(music\.youtube\.com|youtube\.com|youtu\.be)", re.I)

def is_url(text: str) -> bool:
    return text.startswith(("http://", "https://", "www.")) or YTM_HOST_RE.search(text) is not None

def parse_ytm_url(url: str) -> dict:
    """
    Parse a YouTube Music / YouTube URL and return what we found.
    Returns a dict with keys: type ('playlist'|'album_olak'|'video'|'unknown'),
    and 'id'.

    Supported patterns
    ──────────────────
    Album (YTMusic browse link):
      https://music.youtube.com/browse/MPREb_XXXXXXXXXXXXXXX
    Playlist (YTMusic or YT):
      https://music.youtube.com/playlist?list=PLxxxxxxxx
      https://www.youtube.com/playlist?list=PLxxxxxxxx
    Video:
      https://music.youtube.com/watch?v=XXXXXXXXXXX
      https://www.youtube.com/watch?v=XXXXXXXXXXX
    OLAK5 (album via playlist id):
      ...?list=OLAK5uy_XXXXXXXX
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    path = parsed.path

    # browse/MPRB_ → YTMusic album browseId
    if "/browse/" in path:
        browse_id = path.split("/browse/")[-1].split("?")[0].strip("/")
        if browse_id.startswith("MPREb_"):
            return {"type": "album_browse", "id": browse_id}

    # playlist?list=OLAK5uy_  → album
    if "list" in qs:
        list_id = qs["list"][0]
        if list_id.startswith("OLAK5uy_"):
            return {"type": "album_olak", "id": list_id}
        return {"type": "playlist", "id": list_id}

    # watch?v=
    if "v" in qs:
        return {"type": "video", "id": qs["v"][0]}

    return {"type": "unknown", "id": ""}


# ─────────────────────────────────────────────────────────────
#  Playback
# ─────────────────────────────────────────────────────────────

def _stream_url(video_id: str) -> str | None:
    """Resolve a YouTube video_id to a direct audio stream URL via yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("url")
    except Exception as exc:
        error(f"yt-dlp error for {video_id}: {exc}")
        return None


def play_track(video_id: str, title: str, artists: str, track_num: int | None = None, total: int | None = None) -> None:
    """Stream a single track through mpv (audio only)."""
    prefix = f"[{track_num}/{total}] " if track_num and total else ""
    print()
    divider()
    print(c(f"  ▶  {prefix}{title}", GREEN, bold=True))
    print(c(f"       by {artists}", GREY))
    divider()
    print(c("  Resolving stream…", DIM + CYAN))

    stream = _stream_url(video_id)
    if not stream:
        error("Could not resolve audio stream, skipping.")
        return

    print(c("  🎵 Playing! Press Ctrl+C to skip / stop.", YELLOW))
    try:
        subprocess.run(
            ["mpv", "--no-video", "--really-quiet", stream],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except KeyboardInterrupt:
        print(c("\n  ⏭  Skipped.", YELLOW))
    except FileNotFoundError:
        error("'mpv' not found. Install it with: sudo apt install mpv  (or brew install mpv)")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
#  Search helpers
# ─────────────────────────────────────────────────────────────

def _fmt_artists(artists_list) -> str:
    if not artists_list:
        return "Unknown"
    return ", ".join(
        a.get("name", "") if isinstance(a, dict) else str(a)
        for a in artists_list
    )


def search_songs(ytm: YTMusic, query: str, limit: int = 8) -> list[dict]:
    return ytm.search(query, filter="songs", limit=limit)


def search_albums(ytm: YTMusic, query: str, limit: int = 6) -> list[dict]:
    return ytm.search(query, filter="albums", limit=limit)


def search_playlists(ytm: YTMusic, query: str, limit: int = 6) -> list[dict]:
    return ytm.search(query, filter="playlists", limit=limit)


# ─────────────────────────────────────────────────────────────
#  Display result lists & let user pick
# ─────────────────────────────────────────────────────────────

def _pick(prompt: str, items: list, label_fn) -> int | None:
    """Show numbered list, return 0-based index or None if cancelled."""
    for i, item in enumerate(items, 1):
        print(c(f"  [{i}]", CYAN, bold=True) + f" {label_fn(item)}")
    divider(char="·")
    print(c("  [0]", GREY) + " ← back / cancel")
    while True:
        try:
            raw = input(c(f"\n  {prompt}: ", MAGENTA, bold=True)).strip()
            if raw == "0" or raw == "":
                return None
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return idx
            warn(f"Please enter a number between 1 and {len(items)}.")
        except ValueError:
            warn("Enter a valid number.")
        except KeyboardInterrupt:
            return None


# ─────────────────────────────────────────────────────────────
#  Feature 1 – Search & play a song
# ─────────────────────────────────────────────────────────────

def feature_search_song(ytm: YTMusic) -> None:
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

    def label(s):
        title   = s.get("title", "?")
        artists = _fmt_artists(s.get("artists"))
        dur     = s.get("duration", "")
        return f"{c(title, WHITE, bold=True)} {c('by', DIM+GREY)} {c(artists, YELLOW)}  {c(dur, DIM+GREY)}"

    idx = _pick("Pick a song to play", results, label)
    if idx is None:
        return

    song    = results[idx]
    vid     = song.get("videoId")
    title   = song.get("title", "?")
    artists = _fmt_artists(song.get("artists"))

    if not vid:
        error("No video ID found for this song.")
        return

    play_track(vid, title, artists)


# ─────────────────────────────────────────────────────────────
#  Feature 2 – Search & play an album
# ─────────────────────────────────────────────────────────────

def play_album_by_browse_id(ytm: YTMusic, browse_id: str, album_title: str = "") -> None:
    info(f"Fetching album tracks…")
    try:
        album = ytm.get_album(browse_id)
    except Exception as exc:
        error(f"Could not fetch album: {exc}")
        return

    title  = album.get("title", album_title or "Unknown Album")
    artist = _fmt_artists(album.get("artists"))
    year   = album.get("year", "")
    tracks = album.get("tracks", [])

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
        t_title   = t.get("title", "?")
        t_artists = _fmt_artists(t.get("artists"))
        dur       = t.get("duration", "")
        avail     = t.get("isAvailable", True)
        avail_str = "" if avail else c(" [unavailable]", RED)
        print(
            c(f"  {i:>2}.", DIM + GREY)
            + f" {c(t_title, WHITE)}"
            + c(f" – {t_artists}", GREY)
            + c(f"  {dur}", DIM + GREY)
            + avail_str
        )

    divider()
    print(c("  [A] Play all   [P] Pick a track   [0] Back", CYAN))
    choice = input(c("\n  Your choice: ", MAGENTA, bold=True)).strip().upper()

    if choice == "0" or choice == "":
        return

    if choice == "A":
        print(c(f"\n  ▶▶  Playing full album: {title}", GREEN, bold=True))
        for i, t in enumerate(tracks, 1):
            if not t.get("isAvailable", True):
                warn(f"Track {i} ({t.get('title','?')}) is unavailable, skipping.")
                continue
            vid = t.get("videoId")
            if not vid:
                warn(f"Track {i} has no video ID, skipping.")
                continue
            try:
                play_track(
                    vid,
                    t.get("title", "?"),
                    _fmt_artists(t.get("artists")),
                    track_num=i,
                    total=len(tracks),
                )
            except KeyboardInterrupt:
                print(c("\n  ⏹  Album playback stopped.", YELLOW))
                return
        success("Album finished!")

    elif choice == "P":
        available = [(i, t) for i, t in enumerate(tracks, 1) if t.get("isAvailable", True) and t.get("videoId")]
        if not available:
            warn("No available tracks to pick.")
            return

        def label(item):
            i, t = item
            return (
                c(f"{i:>2}.", DIM + GREY)
                + f" {c(t.get('title','?'), WHITE)}"
                + c(f" – {_fmt_artists(t.get('artists'))}", GREY)
            )

        picked = _pick("Pick a track", available, label)
        if picked is None:
            return
        _, t = available[picked]
        play_track(t["videoId"], t.get("title","?"), _fmt_artists(t.get("artists")))


def feature_search_album(ytm: YTMusic) -> None:
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

    def label(a):
        title   = a.get("title", "?")
        artists = _fmt_artists(a.get("artists"))
        year    = a.get("year", "")
        return f"{c(title, WHITE, bold=True)} {c('by', DIM+GREY)} {c(artists, YELLOW)}  {c(year, DIM+GREY)}"

    idx = _pick("Pick an album", results, label)
    if idx is None:
        return

    album   = results[idx]
    browse  = album.get("browseId")
    if not browse:
        error("No browseId for this album.")
        return

    play_album_by_browse_id(ytm, browse, album.get("title", ""))


# ─────────────────────────────────────────────────────────────
#  Feature 3 – Play from a YouTube Music URL (album or playlist)
# ─────────────────────────────────────────────────────────────

def play_playlist_from_id(ytm: YTMusic, playlist_id: str, name: str = "") -> None:
    """Fetch and play a YT Music playlist by its playlist ID."""
    info(f"Fetching playlist…")
    try:
        pl = ytm.get_playlist(playlist_id, limit=None)
    except Exception as exc:
        error(f"Could not fetch playlist: {exc}")
        return

    pl_title  = pl.get("title", name or "Unknown Playlist")
    pl_author = pl.get("author", {})
    if isinstance(pl_author, dict):
        pl_author = pl_author.get("name", "Unknown")
    tracks = pl.get("tracks", [])

    print()
    divider("═")
    print(c(f"  📋  {pl_title}", MAGENTA, bold=True))
    print(c(f"       by {pl_author}", GREY))
    print(c(f"       {len(tracks)} tracks", DIM + CYAN))
    divider("═")

    for i, t in enumerate(tracks, 1):
        t_title   = t.get("title", "?")
        t_artists = _fmt_artists(t.get("artists"))
        dur       = t.get("duration", "")
        print(
            c(f"  {i:>2}.", DIM + GREY)
            + f" {c(t_title, WHITE)}"
            + c(f" – {t_artists}", GREY)
            + c(f"  {dur}", DIM + GREY)
        )

    divider()
    print(c("  [A] Play all   [P] Pick a track   [0] Back", CYAN))
    choice = input(c("\n  Your choice: ", MAGENTA, bold=True)).strip().upper()

    if choice == "0" or choice == "":
        return

    if choice == "A":
        print(c(f"\n  ▶▶  Playing full playlist: {pl_title}", GREEN, bold=True))
        for i, t in enumerate(tracks, 1):
            vid = t.get("videoId")
            if not vid:
                warn(f"Track {i} has no video ID, skipping.")
                continue
            try:
                play_track(
                    vid,
                    t.get("title", "?"),
                    _fmt_artists(t.get("artists")),
                    track_num=i,
                    total=len(tracks),
                )
            except KeyboardInterrupt:
                print(c("\n  ⏹  Playlist playback stopped.", YELLOW))
                return
        success("Playlist finished!")

    elif choice == "P":
        available = [(i, t) for i, t in enumerate(tracks, 1) if t.get("videoId")]

        def label(item):
            i, t = item
            return (
                c(f"{i:>2}.", DIM + GREY)
                + f" {c(t.get('title','?'), WHITE)}"
                + c(f" – {_fmt_artists(t.get('artists'))}", GREY)
            )

        picked = _pick("Pick a track", available, label)
        if picked is None:
            return
        _, t = available[picked]
        play_track(t["videoId"], t.get("title","?"), _fmt_artists(t.get("artists")))


def feature_play_from_url(ytm: YTMusic) -> None:
    url = input(c("\n  🔗 Paste a YouTube Music URL: ", CYAN, bold=True)).strip()
    if not url:
        return

    parsed = parse_ytm_url(url)
    kind   = parsed["type"]
    pid    = parsed["id"]

    if kind == "album_browse":
        # Direct album browseId
        play_album_by_browse_id(ytm, pid)

    elif kind == "album_olak":
        # Need to convert the OLAK5 playlist ID to an album browseId
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
        error("Unrecognised URL format. Supported: album browse links, playlist links, OLAK5 links, video links.")


# ─────────────────────────────────────────────────────────────
#  Feature 4 – Search playlists
# ─────────────────────────────────────────────────────────────

def feature_search_playlist(ytm: YTMusic) -> None:
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

    def label(p):
        title = p.get("title", "?")
        count = p.get("itemCount", "?")
        author = p.get("author", "?")
        if isinstance(author, list) and author:
            author = author[0].get("name", "?")
        return f"{c(title, WHITE, bold=True)} {c('by', DIM+GREY)} {c(str(author), YELLOW)}  {c(str(count)+' tracks', DIM+GREY)}"

    idx = _pick("Pick a playlist", results, label)
    if idx is None:
        return

    pl      = results[idx]
    pl_id   = pl.get("playlistId")
    if not pl_id:
        error("No playlistId found.")
        return

    play_playlist_from_id(ytm, pl_id, pl.get("title", ""))


# ─────────────────────────────────────────────────────────────
#  Main menu
# ─────────────────────────────────────────────────────────────

MENU = [
    ("🎵", "Search & play a Song",           feature_search_song),
    ("💿", "Search & play an Album",          feature_search_album),
    ("📋", "Search & play a Playlist",        feature_search_playlist),
    ("🔗", "Play from a URL (album/playlist)", feature_play_from_url),
]


def main_menu(ytm: YTMusic) -> None:
    while True:
        print()
        divider("═")
        print(c("  MAIN MENU", CYAN, bold=True))
        divider(char="─")
        for i, (icon, label, _) in enumerate(MENU, 1):
            print(c(f"  [{i}]", CYAN, bold=True) + f" {icon}  {label}")
        divider(char="─")
        print(c("  [0]", GREY) + "  Quit")
        divider("═")

        try:
            choice = input(c("\n  Choose an option: ", MAGENTA, bold=True)).strip()
        except (KeyboardInterrupt, EOFError):
            print(c("\n\n  Goodbye! 🎶", CYAN, bold=True))
            sys.exit(0)

        if choice == "0":
            print(c("\n  Goodbye! 🎶", CYAN, bold=True))
            sys.exit(0)

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(MENU):
                _, _, fn = MENU[idx]
                try:
                    fn(ytm)
                except KeyboardInterrupt:
                    print(c("\n  Interrupted – back to menu.", YELLOW))
            else:
                warn(f"Enter a number between 1 and {len(MENU)}, or 0 to quit.")
        except ValueError:
            warn("Invalid input.")


# ─────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────

def main() -> None:
    header()
    ytm = get_ytmusic()
    success("Connected to YouTube Music (unauthenticated mode)")
    main_menu(ytm)


if __name__ == "__main__":
    main()
