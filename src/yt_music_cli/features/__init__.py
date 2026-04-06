"""features package — re-exports all main-menu feature functions.

Adding a new feature means creating a new module here and adding
a single import line.  No other file needs to change (Open/Closed).
"""

from .songs import feature_search_song
from .albums import feature_search_album
from .playlists import feature_search_playlist
from .url_play import feature_play_from_url
from .my_library import feature_my_library

__all__ = [
    "feature_search_song",
    "feature_search_album",
    "feature_search_playlist",
    "feature_play_from_url",
    "feature_my_library",
]
