"""Audio playback.

Single Responsibility: resolves and plays audio — either via a streaming
URL (yt-dlp → mpv) or from a local file (mpv).
No search, no library management, no UI beyond now-playing banners.
"""

from __future__ import annotations

import subprocess
import sys

import yt_dlp

from .ui import c, divider, error, GREEN, GREY, CYAN, YELLOW, DIM


# ── Internal helpers ──────────────────────────────────────────────────────────

def _stream_url(video_id: str) -> str | None:
    """Resolve a YouTube *video_id* to a direct audio-stream URL via yt-dlp.

    Returns the URL string, or ``None`` on failure.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts: dict = {
        "format":      "bestaudio/best",
        "quiet":       True,
        "no_warnings": True,
        "noplaylist":  True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(url, download=False)
            return meta.get("url")  # type: ignore[return-value]
    except Exception as exc:
        error(f"yt-dlp error for {video_id}: {exc}")
        return None


def _launch_mpv(source: str) -> None:
    """Spawn mpv in audio-only quiet mode.  Raises ``FileNotFoundError``
    if mpv is not installed."""
    try:
        subprocess.run(
            ["mpv", "--no-video", "--really-quiet", source],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        error("'mpv' not found.  Install: sudo apt install mpv")
        sys.exit(1)


def _print_now_playing(
    title: str,
    artists: str,
    track_num: int | None = None,
    total: int | None = None,
    offline: bool = False,
) -> None:
    prefix = f"[{track_num}/{total}] " if track_num and total else ""
    print()
    divider()
    print(c(f"  ▶  {prefix}{title}", GREEN, bold=True))
    print(c(f"       by {artists}", GREY))
    if offline:
        print(c("       💾 Offline", DIM + CYAN))
    divider()


# ── Public API ────────────────────────────────────────────────────────────────

def play_track(
    video_id: str,
    title: str,
    artists: str,
    track_num: int | None = None,
    total: int | None = None,
) -> None:
    """Stream a single track from YouTube through mpv (audio only)."""
    _print_now_playing(title, artists, track_num, total)
    print(c("  Resolving stream…", DIM + CYAN))

    stream = _stream_url(video_id)
    if not stream:
        error("Could not resolve audio stream, skipping.")
        return

    print(c("  🎵 Playing! Press Ctrl+C to skip / stop.", YELLOW))
    try:
        _launch_mpv(stream)
    except KeyboardInterrupt:
        print(c("\n  ⏭  Skipped.", YELLOW))


def play_local_file(
    filepath: str,
    title: str,
    artists: str,
    track_num: int | None = None,
    total: int | None = None,
) -> None:
    """Play a locally downloaded audio file through mpv (no network needed)."""
    _print_now_playing(title, artists, track_num, total, offline=True)
    print(c("  🎵 Playing! Press Ctrl+C to skip / stop.", YELLOW))
    try:
        _launch_mpv(filepath)
    except KeyboardInterrupt:
        print(c("\n  ⏭  Skipped.", YELLOW))
