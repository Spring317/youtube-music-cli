"""Terminal colour and formatting primitives.

Single Responsibility: knows *only* how to render text in the terminal.
No business logic, no I/O beyond stdout.
"""

from __future__ import annotations

from typing import Any, Callable

# ── ANSI escape codes ──────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
GREY    = "\033[90m"


def c(text: str, colour: str, bold: bool = False) -> str:
    """Return *text* wrapped in ANSI colour / bold escape codes."""
    prefix = BOLD if bold else ""
    return f"{prefix}{colour}{text}{RESET}"


def header() -> None:
    """Print the application banner."""
    from .config import VERSION  # local import avoids circular deps
    print(c(f"""
╔══════════════════════════════════════════════════╗
║   🎵   YouTube Music CLI Player  v{VERSION}   🎵      ║
║        Powered by ytmusicapi + yt-dlp            ║
╚══════════════════════════════════════════════════╝""", CYAN, bold=True))


def divider(char: str = "─", width: int = 52, colour: str = GREY) -> None:
    """Print a horizontal rule."""
    print(c(char * width, colour))


def success(msg: str) -> None:
    print(c(f"  ✔  {msg}", GREEN))


def warn(msg: str) -> None:
    print(c(f"  ⚠  {msg}", YELLOW))


def error(msg: str) -> None:
    print(c(f"  ✖  {msg}", RED))


def info(msg: str) -> None:
    print(c(f"  ℹ  {msg}", CYAN))


def pick(
    prompt: str,
    items: list[Any],
    label_fn: Callable[[Any], str],
) -> int | None:
    """Display a numbered chooser and return the chosen 0-based index.

    Returns ``None`` when the user cancels (enters ``0`` or presses Ctrl+C).
    """
    for i, item in enumerate(items, 1):
        print(c(f"  [{i}]", CYAN, bold=True) + f" {label_fn(item)}")
    divider(char="·")
    print(c("  [0]", GREY) + " ← back / cancel")
    while True:
        try:
            raw = input(c(f"\n  {prompt}: ", MAGENTA, bold=True)).strip()
            if raw in ("0", ""):
                return None
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return idx
            warn(f"Please enter a number between 1 and {len(items)}.")
        except ValueError:
            warn("Enter a valid number.")
        except KeyboardInterrupt:
            return None
