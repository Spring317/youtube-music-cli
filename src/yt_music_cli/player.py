"""Audio playback.

Single Responsibility: resolves and plays audio — either via a streaming
URL (yt-dlp → mpv) or from a local file (mpv).
No search, no library management, no UI beyond now-playing banners.
"""

from __future__ import annotations

import json
import os
import queue
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import termios
import threading
import time
import tty

import yt_dlp

from .search import fmt_artists
from .ui import CYAN, DIM, GREEN, GREY, YELLOW, c, divider, error

# ── Internal helpers ──────────────────────────────────────────────────────────

# JS runtimes yt-dlp supports, checked in preference order.
# Deno is yt-dlp's default but is rarely pre-installed; Node.js is common.
_JS_RUNTIME_CANDIDATES: list[tuple[str, list[str]]] = [
    ("deno", ["deno"]),
    ("node", ["node", "nodejs"]),
    ("bun", ["bun"]),
    ("quickjs", ["qjs"]),
]

# Browser name (as yt-dlp understands it) → candidate binary names on Linux
_BROWSER_CANDIDATES: list[tuple[str, list[str]]] = [
    ("chromium", ["chromium", "chromium-browser"]),
    ("chrome", ["google-chrome", "google-chrome-stable", "chrome"]),
    ("firefox", ["firefox", "firefox-esr"]),
    ("brave", ["brave-browser", "brave"]),
    ("edge", ["microsoft-edge", "microsoft-edge-stable"]),
    ("opera", ["opera"]),
    ("vivaldi", ["vivaldi"]),
]


def _detect_js_runtime() -> str | None:
    """Return the yt-dlp runtime key for the first installed JS engine found."""
    for runtime_name, binaries in _JS_RUNTIME_CANDIDATES:
        if any(shutil.which(b) for b in binaries):
            return runtime_name
    return None


def _detect_browser() -> str | None:
    """Return the yt-dlp browser name for the first installed browser found."""
    for browser_name, binaries in _BROWSER_CANDIDATES:
        if any(shutil.which(b) for b in binaries):
            return browser_name
    return None


def _get_ydl_opts() -> dict:
    """Build yt-dlp options with the best available JS runtime and cookie source.

    JS runtime priority (required for YouTube signature solving):
      1. Deno  2. Node  3. Bun  4. QuickJS

    Cookie priority:
      1. ``~/.ytmusic_cli/cookies.txt``  – user-managed Netscape cookie file
      2. Auto-detected installed browser  – yt-dlp extracts cookies itself
      3. No cookies                       – may fail on bot-detected IPs
    """
    from .config import COOKIES_FILE

    opts: dict = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    # YouTube now requires an external JS runtime to solve signature challenges.
    js_runtime = _detect_js_runtime()
    if js_runtime:
        opts["js_runtimes"] = {js_runtime: {}}
    # If no runtime found, yt-dlp will try its default (deno) and fail with a
    # clear message, so we don't need to abort here.

    if COOKIES_FILE.exists():
        opts["cookiefile"] = str(COOKIES_FILE)
    else:
        browser = _detect_browser()
        if browser:
            opts["cookiesfrombrowser"] = (browser,)

    return opts


def _stream_url(video_id: str) -> str | None:
    """Resolve a YouTube *video_id* to a direct audio-stream URL via yt-dlp.

    Returns the URL string, or ``None`` on failure.
    """
    from .config import COOKIES_FILE

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(_get_ydl_opts()) as ydl:
            meta = ydl.extract_info(url, download=False)
            return meta.get("url")  # type: ignore[return-value]
    except Exception as exc:
        msg = str(exc)
        if "Sign in" in msg or "bot" in msg.lower() or "cookies" in msg.lower():
            error(
                f"YouTube blocked playback for {video_id} (bot detection).\n"
                f"  Auto-fix: ensure a supported browser (Firefox, Chrome …) is\n"
                f"            installed — cookies are read from it automatically.\n"
                f"  Manual fix: export cookies to {COOKIES_FILE}\n"
                f"  Guide: https://github.com/yt-dlp/yt-dlp/wiki/FAQ"
                f"#how-do-i-pass-cookies-to-yt-dlp"
            )
        else:
            error(f"yt-dlp error for {video_id}: {exc}")
        return None


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


# ── Player Manager ────────────────────────────────────────────────────────────


class PlayerManager:
    """Manages an MPV process for gapless playlist playback using IPC."""

    def __init__(self, tracks: list[dict], playlist_title: str = ""):
        self.tracks = [t for t in tracks if t.get("videoId")]
        self.playlist_title = playlist_title

        self.socket_path = tempfile.mktemp(prefix="ytm_mpv_sock_")

        self.mpv_proc: subprocess.Popen | None = None
        self.ipc_sock: socket.socket | None = None
        self._running = False

        self.mpv_playlist: list[dict] = []
        self.mpv_pos = -1

        self.resolve_queue = queue.Queue()
        self.resolver_thread = threading.Thread(target=self._resolver_loop, daemon=True)
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.keyboard_thread = threading.Thread(target=self._keyboard_loop, daemon=True)

    def start(self):
        if not self.tracks:
            return

        self._running = True

        try:
            self.mpv_proc = subprocess.Popen(
                [
                    "mpv",
                    "--no-video",
                    "--really-quiet",
                    "--idle=yes",
                    f"--input-ipc-server={self.socket_path}",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            error("'mpv' not found.  Install: sudo apt install mpv")
            sys.exit(1)

        start_time = time.time()
        while time.time() - start_time < 3.0:
            if os.path.exists(self.socket_path):
                break
            time.sleep(0.1)

        if not os.path.exists(self.socket_path):
            error("Could not connect to mpv via IPC.")
            self.stop()
            return

        self.ipc_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.ipc_sock.connect(self.socket_path)
            self._send_cmd(["observe_property", 1, "playlist-pos"])
            self._send_cmd(["observe_property", 2, "pause"])
        except Exception as e:
            error(f"Failed IPC connection: {e}")
            self.stop()
            return

        self.resolver_thread.start()
        self.listener_thread.start()
        self.keyboard_thread.start()

        # Start preloading the first song
        self.resolve_queue.put(self.tracks[0])

        print()
        if self.playlist_title:
            print(c(f"  ▶▶  Playing playlist: {self.playlist_title}", GREEN, bold=True))
        print(
            c(
                "  🎵 Controls: [P] Pause | [Left] Prev | [Right] Next | [Q] Quit",
                YELLOW,
            )
        )

        try:
            self.mpv_proc.wait()
        except KeyboardInterrupt:
            print(c("\n  ⏭  Playback cancelled.", YELLOW))
        finally:
            self.stop()

    def stop(self):
        self._running = False
        if self.mpv_proc and self.mpv_proc.poll() is None:
            self.mpv_proc.terminate()
            self.mpv_proc.wait()

        if self.ipc_sock:
            self.ipc_sock.close()

        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

    def _send_cmd(self, cmd: list):
        if self.ipc_sock:
            try:
                msg = json.dumps({"command": cmd}).encode("utf-8") + b"\n"
                self.ipc_sock.sendall(msg)
            except Exception:
                pass

    def _resolver_loop(self):
        while self._running:
            try:
                track = self.resolve_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            vid = track.get("videoId")
            if not vid:
                self.resolve_queue.task_done()
                continue

            url = _stream_url(vid)
            if url and self._running:
                self.mpv_playlist.append(track)
                self._send_cmd(["loadfile", url, "append"])

                # If mpv is bare idle, start playback on the newly appended track
                if len(self.mpv_playlist) == 1 or self.mpv_pos == -1:
                    self._send_cmd(
                        ["set_property", "playlist-pos", len(self.mpv_playlist) - 1]
                    )
                    self._send_cmd(["set_property", "pause", False])

            self.resolve_queue.task_done()

    def _listener_loop(self):
        f = self.ipc_sock.makefile("r") if self.ipc_sock else None
        if not f:
            return

        is_paused = False

        while self._running:
            try:
                line = f.readline()
                if not line:
                    break

                data = json.loads(line)
                if "event" not in data:
                    continue

                evt = data["event"]

                if evt == "client-message":
                    args = data.get("args", [])
                    if "skip-next" in args:
                        self._skip_next()
                    elif "skip-prev" in args:
                        self._skip_prev()
                    elif "toggle-pause" in args:
                        self._send_cmd(["set_property", "pause", not is_paused])

                elif evt == "property-change":
                    prop_name = data.get("name")
                    if prop_name == "pause":
                        is_paused = data.get("data", False)

                    elif prop_name == "playlist-pos":
                        pos = data.get("data")
                        if pos is not None and pos != self.mpv_pos:
                            self.mpv_pos = pos
                            self._on_track_changed()

                elif evt == "idle":
                    self._check_end_of_playlist()

            except Exception:
                break

    def _skip_next(self):
        if self.mpv_pos + 1 < len(self.mpv_playlist):
            self._send_cmd(["playlist-next", "force"])
        else:
            # We haven't buffered the next track yet, force advance track pointer
            # So the resolver loop knows what to do, or the player just goes idle and waits
            pass

    def _skip_prev(self):
        if self.mpv_pos > 0:
            self._send_cmd(["playlist-prev", "force"])
        else:
            self._send_cmd(["seek", 0, "absolute"])

    def _on_track_changed(self):
        if 0 <= self.mpv_pos < len(self.mpv_playlist):
            track = self.mpv_playlist[self.mpv_pos]
            _print_now_playing(
                title=track.get("title", "?"),
                artists=fmt_artists(track.get("artists")),
                track_num=self.tracks.index(track) + 1
                if track in self.tracks
                else None,
                total=len(self.tracks),
            )
            self._enqueue_next()

    def _enqueue_next(self):
        try:
            current_track = self.mpv_playlist[self.mpv_pos]
            original_idx = self.tracks.index(current_track)
            next_idx = original_idx + 1
            if next_idx < len(self.tracks):
                next_track = self.tracks[next_idx]
                if next_track not in self.mpv_playlist:
                    self.resolve_queue.put(next_track)
        except ValueError:
            pass

    def _keyboard_loop(self):
        """Read raw keypresses from the terminal and send IPC commands to mpv.

        This is necessary because mpv runs detached from the terminal
        (stdin=DEVNULL), so it never receives keyboard input on its own.
        We capture keypresses here in Python and forward them as IPC commands.
        """
        if not sys.stdin.isatty():
            return

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            # setcbreak: single-keypress input, no echo, but keeps OPOST so
            # \n is still translated to \r\n — safe for concurrent print() calls.
            tty.setcbreak(fd)
            while self._running:
                # Poll stdin with a short timeout so we can check _running
                ready, _, _ = select.select([sys.stdin], [], [], 0.2)
                if not ready:
                    continue

                ch = sys.stdin.read(1)

                if ch in ("p", "P", " "):  # pause / resume
                    self._send_cmd(["cycle", "pause"])

                elif ch in ("q", "Q"):  # quit
                    self._running = False
                    self._send_cmd(["quit"])
                    return

                elif ch == "\x1b":  # ESC — start of arrow-key sequence
                    r2, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if not r2:
                        continue
                    ch2 = sys.stdin.read(1)
                    if ch2 != "[":
                        continue
                    r3, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if not r3:
                        continue
                    ch3 = sys.stdin.read(1)
                    if ch3 == "D":  # ← Left arrow  → previous track
                        self._skip_prev()
                    elif ch3 == "C":  # → Right arrow → next track
                        self._skip_next()

        except Exception:
            pass
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

    def _check_end_of_playlist(self):
        if self.mpv_pos == -1 and len(self.mpv_playlist) == 0:
            return  # still resolving first track

        if self.mpv_pos >= len(self.mpv_playlist) - 1:
            try:
                last_queued = self.mpv_playlist[-1]
                idx = self.tracks.index(last_queued)
                if idx == len(self.tracks) - 1:
                    self._running = False
                    self._send_cmd(["quit"])
            except ValueError:
                pass


# ── Public API ────────────────────────────────────────────────────────────────


def play_playlist(tracks: list[dict], title: str = "") -> None:
    """Seamlessly play a list of tracks with gapless playback."""
    manager = PlayerManager(tracks, title)
    manager.start()


def play_track(
    video_id: str,
    title: str,
    artists: str,
    track_num: int | None = None,
    total: int | None = None,
) -> None:
    """Stream a single track (wraps play_playlist internally)."""
    track = {"videoId": video_id, "title": title, "artists": artists}
    play_playlist([track], title)


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
        subprocess.run(
            ["mpv", "--no-video", "--really-quiet", filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        error("'mpv' not found.  Install: sudo apt install mpv")
        sys.exit(1)
    except KeyboardInterrupt:
        print(c("\n  ⏭  Skipped.", YELLOW))
