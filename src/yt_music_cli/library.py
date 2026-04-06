"""Saved-item library: token persistence and offline downloading.

Single Responsibility: knows how to persist (save / load) playlists and
albums as JSON tokens, and how to download audio files via yt-dlp.
Does NOT know how tracks are played — that is player.py's concern.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import yt_dlp

from .config import SAVE_DIR, OFFLINE_DIR, MP3_QUALITY, ensure_dirs
from .models import Track, SavedToken
from .search import fmt_artists
from .ui import success, warn, error, info, c, divider, MAGENTA, GREY, CYAN


# ── Private helpers ───────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Return a filesystem-safe version of *name*."""
    return re.sub(r"[^\w\-. ]", "_", name).strip().replace(" ", "_")


def _normalise_tracks(raw_tracks: list[dict[str, Any]]) -> list[Track]:
    """Convert ytmusicapi track dicts to :class:`Track` format.

    Entries without a ``videoId`` are silently discarded.
    """
    result: list[Track] = []
    for t in raw_tracks:
        vid = t.get("videoId")
        if not vid:
            continue
        track: Track = {
            "videoId":  vid,
            "title":    t.get("title", "?"),
            "artists":  fmt_artists(t.get("artists")),
            "duration": t.get("duration", ""),
        }
        if "isAvailable" in t:
            track["isAvailable"] = bool(t["isAvailable"])
        result.append(track)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def save_token(
    kind: str,
    title: str,
    author: str,
    tracks: list[dict[str, Any]],
    browse_id: str = "",
    playlist_id: str = "",
) -> None:
    """Persist playlist / album metadata as a JSON token for quick re-play.

    No audio is downloaded — only track IDs and metadata are stored so the
    library can stream the content later without re-querying the search API.
    """
    ensure_dirs()
    token: SavedToken = {
        "kind":       kind,
        "title":      title,
        "author":     author,
        "browseId":   browse_id,
        "playlistId": playlist_id,
        "savedAt":    time.strftime("%Y-%m-%d %H:%M"),
        "tracks":     _normalise_tracks(tracks),
    }
    filename = _safe_filename(f"{kind}_{title}") + ".json"
    path = SAVE_DIR / filename
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(token, fh, ensure_ascii=False, indent=2)
    success(f"Saved token → {path}")
    info(f"  {len(token['tracks'])} tracks stored. Re-play from 'My Library'.")


def download_offline(
    kind: str,
    title: str,
    author: str,
    tracks: list[dict[str, Any]],
    browse_id: str = "",
    playlist_id: str = "",
) -> None:
    """Download all available tracks as 192 kbps MP3 files via yt-dlp.

    Also writes a token that points to the local files so the library
    can play them without a network connection.
    """
    ensure_dirs()
    available = [t for t in tracks if t.get("videoId") and t.get("isAvailable", True)]
    if not available:
        warn("No downloadable tracks found.")
        return

    folder_name = _safe_filename(f"{kind}_{title}")
    dest_dir    = OFFLINE_DIR / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    print()
    divider("═")
    print(c(f"  💾  Downloading offline: {title}", MAGENTA, bold=True))
    print(c(f"       {len(available)} tracks → {dest_dir}", GREY))
    divider("═")

    downloaded: list[Track] = []
    for i, raw in enumerate(available, 1):
        vid       = raw["videoId"]
        t_title   = raw.get("title", "?")
        t_artists = fmt_artists(raw.get("artists"))
        safe_name = _safe_filename(f"{i:02d}_{t_title}")
        out_tmpl  = str(dest_dir / f"{safe_name}.%(ext)s")

        print(c(f"\n  [{i}/{len(available)}] Downloading: {t_title}…", CYAN))
        ydl_opts: dict[str, Any] = {
            "format":      "bestaudio/best",
            "outtmpl":     out_tmpl,
            "quiet":       True,
            "no_warnings": True,
            "noplaylist":  True,
            "postprocessors": [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": MP3_QUALITY,
            }],
        }
        yt_url = f"https://www.youtube.com/watch?v={vid}"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([yt_url])
            matches    = list(dest_dir.glob(f"{safe_name}.*"))
            local_path = str(matches[0]) if matches else ""
            track: Track = {
                "videoId":   vid,
                "title":     t_title,
                "artists":   t_artists,
                "duration":  raw.get("duration", ""),
                "localFile": local_path,
            }
            downloaded.append(track)
            success(f"  ✔  {t_title}")
        except KeyboardInterrupt:
            warn("Download interrupted.")
            break
        except Exception as exc:
            error(f"  Failed to download '{t_title}': {exc}")

    token: SavedToken = {
        "kind":       kind,
        "title":      title,
        "author":     author,
        "browseId":   browse_id,
        "playlistId": playlist_id,
        "savedAt":    time.strftime("%Y-%m-%d %H:%M"),
        "offline":    True,
        "localDir":   str(dest_dir),
        "tracks":     downloaded,
    }
    token_path = SAVE_DIR / (_safe_filename(f"offline_{kind}_{title}") + ".json")
    with open(token_path, "w", encoding="utf-8") as fh:
        json.dump(token, fh, ensure_ascii=False, indent=2)

    print()
    divider()
    success(f"Downloaded {len(downloaded)}/{len(available)} tracks.")
    success(f"Files saved to: {dest_dir}")
    success(f"Token saved: {token_path}")
    info("Play offline from 'My Library'.")


def load_tokens() -> list[SavedToken]:
    """Load and return all saved JSON tokens from :data:`SAVE_DIR`.

    Each dict has ``_path`` injected at runtime for deletion support;
    this field is never written to disk.
    """
    ensure_dirs()
    tokens: list[SavedToken] = []
    for path in sorted(SAVE_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                data: SavedToken = json.load(fh)
                data["_path"] = str(path)  # type: ignore[typeddict-unknown-key]
                tokens.append(data)
        except Exception:
            pass
    return tokens
