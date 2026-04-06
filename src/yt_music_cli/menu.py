"""Main menu: defines the MENU registry and drives the interactive loop.

Single Responsibility: knows which features exist and how to present
and dispatch them.  Does not implement any feature itself.

New features are added by appending one tuple to ``MENU`` — no other
change is needed (Open/Closed Principle).
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from ytmusicapi import YTMusic

from .ui import c, divider, warn, MAGENTA, CYAN, GREY, YELLOW
from .features import (
    feature_search_song,
    feature_search_album,
    feature_search_playlist,
    feature_play_from_url,
    feature_my_library,
)

# Type alias: every feature function accepts a YTMusic instance and returns None.
FeatureFn = Callable[[YTMusic], None]

# Registry: (icon, label, handler)
MENU: list[tuple[str, str, FeatureFn]] = [
    ("🎵", "Search & play a Song",            feature_search_song),
    ("💿", "Search & play an Album",           feature_search_album),
    ("📋", "Search & play a Playlist",         feature_search_playlist),
    ("🔗", "Play from a URL (album/playlist)", feature_play_from_url),
    ("📚", "My Library  (saved / offline)",    feature_my_library),
]


def main_menu(ytm: YTMusic) -> None:
    """Run the interactive main-menu loop until the user quits."""
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
