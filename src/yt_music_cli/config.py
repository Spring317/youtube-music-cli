"""Application-level configuration: version, storage paths, and constants.

Single Responsibility: the only place that knows *where* things are stored
and what build version is running.  Nothing else imports anything from here
except values – no business logic lives here.
"""

from pathlib import Path

VERSION: str = "2.1"
MP3_QUALITY: str = "192"

# Storage directories
SAVE_DIR: Path = Path.home() / ".ytmusic_cli" / "saved"
OFFLINE_DIR: Path = Path.home() / "Music" / "ytmusic"


def ensure_dirs() -> None:
    """Create required storage directories if they don't already exist."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
