#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════╗
║     🎵  YouTube Music CLI Player  🎵     ║
║         Powered by ytmusicapi             ║
╚═══════════════════════════════════════════╝
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
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
║   🎵   YouTube Music CLI Player  v2.1   🎵      ║
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
#  Storage paths
# ─────────────────────────────────────────────────────────────

SAVE_DIR    = Path.home() / ".ytmusic_cli" / "saved"   # JSON tokens
OFFLINE_DIR = Path.home() / "Music" / "ytmusic"        # downloaded audio


def ensure_dirs() -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    OFFLINE_DIR.mkdir(parents=True, exist_ok=True)


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


def play_local_file(filepath: str, title: str, artists: str, track_num: int | None = None, total: int | None = None) -> None:
    """Play a locally downloaded audio file through mpv."""
    prefix = f"[{track_num}/{total}] " if track_num and total else ""
    print()
    divider()
    print(c(f"  ▶  {prefix}{title}", GREEN, bold=True))
    print(c(f"       by {artists}", GREY))
    print(c(f"       💾 Offline", DIM + CYAN))
    divider()
    print(c("  🎵 Playing! Press Ctrl+C to skip / stop.", YELLOW))
    try:
        subprocess.run(
            ["mpv", "--no-video", "--really-quiet", filepath],
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
    print(c("  [A] Play all   [P] Pick a track   [S] Save   [D] Download offline   [0] Back", CYAN))
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

    elif choice == "S":
        save_token(
            kind="album",
            title=title,
            author=artist,
            browse_id=browse_id,
            tracks=tracks,
        )

    elif choice == "D":
        download_offline(
            kind="album",
            title=title,
            author=artist,
            browse_id=browse_id,
            tracks=tracks,
        )


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
    print(c("  [A] Play all   [P] Pick a track   [S] Save   [D] Download offline   [0] Back", CYAN))
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

    elif choice == "S":
        save_token(
            kind="playlist",
            title=pl_title,
            author=pl_author,
            playlist_id=playlist_id,
            tracks=tracks,
        )

    elif choice == "D":
        download_offline(
            kind="playlist",
            title=pl_title,
            author=pl_author,
            playlist_id=playlist_id,
            tracks=tracks,
        )


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
#  Save / Library helpers
# ─────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Turn a title into a safe directory/file name."""
    return re.sub(r"[^\w\-. ]", "_", name).strip().replace(" ", "_")


def save_token(kind: str, title: str, author: str, tracks: list, browse_id: str = "", playlist_id: str = "") -> None:
    """
    Save playlist/album metadata as a JSON 'token' for quick re-play.
    No audio is downloaded – just store track IDs and metadata.
    """
    ensure_dirs()

    # Normalise track list to a consistent format
    token_tracks = []
    for t in tracks:
        vid = t.get("videoId")
        if vid:
            token_tracks.append({
                "videoId": vid,
                "title":   t.get("title", "?"),
                "artists": _fmt_artists(t.get("artists")),
                "duration": t.get("duration", ""),
                "isAvailable": t.get("isAvailable", True),
            })

    token = {
        "kind":       kind,          # "album" | "playlist"
        "title":      title,
        "author":     author,
        "browseId":   browse_id,
        "playlistId": playlist_id,
        "savedAt":    time.strftime("%Y-%m-%d %H:%M"),
        "tracks":     token_tracks,
    }

    filename = _safe_filename(f"{kind}_{title}") + ".json"
    path = SAVE_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)

    success(f"Saved token → {path}")
    info(f"  {len(token_tracks)} tracks stored. Re-play from 'My Library' (no internet needed for metadata).")


def download_offline(kind: str, title: str, author: str, tracks: list, browse_id: str = "", playlist_id: str = "") -> None:
    """
    Download all available tracks as audio files (best quality MP3-like)
    using yt-dlp, and save a token so the library knows about them.
    """
    ensure_dirs()

    available = [t for t in tracks if t.get("videoId") and t.get("isAvailable", True)]
    if not available:
        warn("No downloadable tracks found.")
        return

    folder_name = _safe_filename(f"{kind}_{title}")
    dest_dir = OFFLINE_DIR / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    print()
    divider("═")
    print(c(f"  💾  Downloading offline: {title}", MAGENTA, bold=True))
    print(c(f"       {len(available)} tracks → {dest_dir}", GREY))
    divider("═")

    downloaded_tracks = []
    for i, t in enumerate(available, 1):
        vid      = t["videoId"]
        t_title  = t.get("title", "?")
        t_artist = _fmt_artists(t.get("artists"))
        safe_name = _safe_filename(f"{i:02d}_{t_title}")
        out_template = str(dest_dir / f"{safe_name}.%(ext)s")

        print(c(f"\n  [{i}/{len(available)}] Downloading: {t_title}…", CYAN))

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        url = f"https://www.youtube.com/watch?v={vid}"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            # Find the downloaded file
            matches = list(dest_dir.glob(f"{safe_name}.*"))
            local_path = str(matches[0]) if matches else ""
            downloaded_tracks.append({
                "videoId":   vid,
                "title":     t_title,
                "artists":   t_artist,
                "duration":  t.get("duration", ""),
                "localFile": local_path,
            })
            success(f"  ✔  {t_title}")
        except KeyboardInterrupt:
            warn("Download interrupted by user.")
            break
        except Exception as exc:
            error(f"  Failed to download '{t_title}': {exc}")

    # Save a token that points to local files
    token = {
        "kind":       kind,
        "title":      title,
        "author":     author,
        "browseId":   browse_id,
        "playlistId": playlist_id,
        "savedAt":    time.strftime("%Y-%m-%d %H:%M"),
        "offline":    True,
        "localDir":   str(dest_dir),
        "tracks":     downloaded_tracks,
    }

    token_path = SAVE_DIR / (_safe_filename(f"offline_{kind}_{title}") + ".json")
    with open(token_path, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)

    print()
    divider()
    success(f"Downloaded {len(downloaded_tracks)}/{len(available)} tracks.")
    success(f"Files saved to: {dest_dir}")
    success(f"Token saved to: {token_path}")
    info("You can play them offline from 'My Library' → Offline.")


# ─────────────────────────────────────────────────────────────
#  Feature 5 – My Library (saved tokens + offline)
# ─────────────────────────────────────────────────────────────

def _load_tokens() -> list[dict]:
    """Load all saved token JSON files from SAVE_DIR."""
    ensure_dirs()
    tokens = []
    for path in sorted(SAVE_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                data["_path"] = str(path)
                tokens.append(data)
        except Exception:
            pass
    return tokens


def _play_token(token: dict) -> None:
    """Play the tracks stored in a saved token (streaming or local files)."""
    title    = token.get("title", "?")
    author   = token.get("author", "?")
    is_offline = token.get("offline", False)
    tracks   = token.get("tracks", [])

    if not tracks:
        warn("No tracks in this saved item.")
        return

    print()
    divider("═")
    icon = "💾" if is_offline else "🔖"
    print(c(f"  {icon}  {title}", MAGENTA, bold=True))
    print(c(f"       by {author}", GREY))
    mode = c("  Offline 💾", DIM + GREEN) if is_offline else c("  Streaming 🌐", DIM + CYAN)
    print(mode)
    print(c(f"       {len(tracks)} tracks", DIM + CYAN))
    divider("═")

    for i, t in enumerate(tracks, 1):
        t_title  = t.get("title", "?")
        t_artist = t.get("artists", "?")
        dur      = t.get("duration", "")
        avail    = t.get("isAvailable", True)
        avail_str = "" if avail else c(" [unavailable]", RED)
        local    = t.get("localFile", "")
        local_str = c(" 💾", DIM + GREEN) if local and Path(local).exists() else ""
        print(
            c(f"  {i:>2}.", DIM + GREY)
            + f" {c(t_title, WHITE)}"
            + c(f" – {t_artist}", GREY)
            + c(f"  {dur}", DIM + GREY)
            + avail_str
            + local_str
        )

    divider()
    print(c("  [A] Play all   [P] Pick a track   [X] Delete saved   [0] Back", CYAN))
    choice = input(c("\n  Your choice: ", MAGENTA, bold=True)).strip().upper()

    if choice == "0" or choice == "":
        return

    if choice == "A":
        print(c(f"\n  ▶▶  Playing: {title}", GREEN, bold=True))
        for i, t in enumerate(tracks, 1):
            vid     = t.get("videoId")
            t_title = t.get("title", "?")
            t_art   = t.get("artists", "?")
            local   = t.get("localFile", "")

            if local and Path(local).exists():
                try:
                    play_local_file(local, t_title, t_art, track_num=i, total=len(tracks))
                except KeyboardInterrupt:
                    print(c("\n  ⏹  Playback stopped.", YELLOW))
                    return
            elif vid:
                try:
                    play_track(vid, t_title, t_art, track_num=i, total=len(tracks))
                except KeyboardInterrupt:
                    print(c("\n  ⏹  Playback stopped.", YELLOW))
                    return
            else:
                warn(f"Track {i} has no video ID and no local file, skipping.")
        success(f"Finished: {title}")

    elif choice == "P":
        available = [
            (i, t) for i, t in enumerate(tracks, 1)
            if t.get("videoId") or (t.get("localFile") and Path(t.get("localFile","")).exists())
        ]
        if not available:
            warn("No playable tracks found.")
            return

        def label(item):
            i, t = item
            local = t.get("localFile", "")
            offline_mark = c(" 💾", DIM + GREEN) if local and Path(local).exists() else ""
            return (
                c(f"{i:>2}.", DIM + GREY)
                + f" {c(t.get('title','?'), WHITE)}"
                + c(f" – {t.get('artists','?')}", GREY)
                + offline_mark
            )

        picked = _pick("Pick a track", available, label)
        if picked is None:
            return
        _, t = available[picked]
        local = t.get("localFile", "")
        if local and Path(local).exists():
            play_local_file(local, t.get("title","?"), t.get("artists","?"))
        elif t.get("videoId"):
            play_track(t["videoId"], t.get("title","?"), t.get("artists","?"))
        else:
            error("No playable source for this track.")

    elif choice == "X":
        path = token.get("_path", "")
        if path and Path(path).exists():
            confirm = input(c(f"\n  Delete '{title}'? [y/N]: ", RED, bold=True)).strip().lower()
            if confirm == "y":
                Path(path).unlink()
                success(f"Deleted: {path}")
                info("Note: downloaded audio files (if any) are NOT deleted.")
            else:
                info("Cancelled.")
        else:
            error("Token file not found.")


def feature_my_library(_ytm: YTMusic) -> None:
    """Show saved playlists/albums (tokens) and let the user play them."""
    tokens = _load_tokens()

    if not tokens:
        print()
        divider()
        print(c("  📚  My Library", BOLD + WHITE))
        divider(char="·")
        warn("No saved items yet.")
        info("Save an album or playlist by pressing [S] or [D] when viewing one.")
        divider()
        return

    while True:
        print()
        divider("═")
        print(c("  📚  My Library", BOLD + WHITE))
        divider(char="·")

        # Reload tokens each loop in case something was deleted
        tokens = _load_tokens()
        if not tokens:
            warn("Library is now empty.")
            return

        def label(tok):
            kind    = tok.get("kind", "?")
            title   = tok.get("title", "?")
            author  = tok.get("author", "?")
            n       = len(tok.get("tracks", []))
            saved   = tok.get("savedAt", "")
            offline = "  💾 Offline" if tok.get("offline") else "  🌐 Token"
            icon    = "💿" if kind == "album" else "📋"
            return (
                f"{icon}  {c(title, WHITE, bold=True)}"
                + c(f" by {author}", GREY)
                + c(f"  {n} tracks", DIM + CYAN)
                + c(offline, DIM + GREEN if tok.get("offline") else DIM + CYAN)
                + c(f"  {saved}", DIM + GREY)
            )

        idx = _pick("Pick an item to play", tokens, label)
        if idx is None:
            return
        _play_token(tokens[idx])


# ─────────────────────────────────────────────────────────────
#  Main menu
# ─────────────────────────────────────────────────────────────

MENU = [
    ("🎵", "Search & play a Song",           feature_search_song),
    ("💿", "Search & play an Album",          feature_search_album),
    ("📋", "Search & play a Playlist",        feature_search_playlist),
    ("🔗", "Play from a URL (album/playlist)", feature_play_from_url),
    ("📚", "My Library  (saved / offline)",   feature_my_library),
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
