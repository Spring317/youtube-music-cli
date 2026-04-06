#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════╗
║     🎵  YouTube Music CLI Player  🎵     ║
║         Powered by ytmusicapi             ║
╚═══════════════════════════════════════════╝

Entry point only.  All logic lives in the sub-modules:

    config.py          – constants & storage paths
    ui.py              – ANSI helpers & pick()
    models.py          – TypedDicts (Track, SavedToken, ParsedUrl)
    url_parser.py      – URL recognition & parsing
    ytmusic_client.py  – YTMusic() factory
    player.py          – audio playback (stream + local)
    search.py          – ytmusicapi search wrappers
    library.py         – save token / download offline / load tokens
    features/          – one file per user-facing feature
    menu.py            – MENU registry + interactive loop
"""

from .ui import header, success
from .ytmusic_client import get_ytmusic
from .menu import main_menu


def main() -> None:
    """Application entry point."""
    header()
    ytm = get_ytmusic()
    success("Connected to YouTube Music (unauthenticated mode)")
    main_menu(ytm)


if __name__ == "__main__":
    main()
