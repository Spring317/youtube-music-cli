# 🎵 YouTube Music CLI Player

A feature-rich, terminal-based YouTube Music player. Search for songs, albums, and playlists, or drop in a YouTube Music link and start listening instantly.

No bulky GUIs, no web browsers — just text and music.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎵 **Song Search** | Search YouTube Music by name or artist, pick from results, and play instantly |
| 💿 **Album Search** | Search for albums, browse the full tracklist, then play all or pick a track |
| 📋 **Playlist Search** | Find public playlists, preview every track, and play all or jump to one |
| 🔗 **Play from URL** | Paste any YouTube Music link — album, playlist, or video — and it just works |

### Supported URL formats
```
https://music.youtube.com/browse/MPREb_…          ← Album (browse link)
https://music.youtube.com/playlist?list=OLAK5uy_… ← Album (playlist link)
https://music.youtube.com/playlist?list=PL…        ← Playlist
https://music.youtube.com/watch?v=…               ← Single track
https://www.youtube.com/watch?v=…                 ← Regular YouTube video
```

> ℹ️ **No login required** — the player works fully unauthenticated for searching, browsing, and playback.

---

## Prerequisites

You need **mpv** installed for audio playback:

**Arch Linux / CachyOS / Manjaro:**
```bash
sudo pacman -S mpv
```

**Ubuntu / Debian:**
```bash
sudo apt install mpv
```

**macOS (Homebrew):**
```bash
brew install mpv
```

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/Spring317/youtube-music-cli.git
cd youtube-music-cli
```

### 2. Create and activate the Conda environment
```bash
conda create -n cli-music python=3.11 -y
conda activate cli-music
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Install the package (dev mode)
```bash
pip install -e .
```

Now you can run it directly:
```bash
ytmusic
```

---

## 🔨 Build a Standalone Binary

Compile everything into a single portable executable using PyInstaller:

```bash
conda activate cli-music
pyinstaller --onefile --collect-data ytmusicapi -n ytmusic src/yt_music_cli/main.py
```

Install it to your PATH:
```bash
mkdir -p ~/.local/bin
mv dist/ytmusic ~/.local/bin/ytmusic
```

Make sure `~/.local/bin` is on your PATH (add to `~/.bashrc` or `~/.zshrc` if needed):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then launch from anywhere:
```bash
ytmusic
```

---

## Usage

On launch you'll see an interactive menu:

```
╔══════════════════════════════════════════════════╗
║   🎵   YouTube Music CLI Player  v2.0   🎵      ║
╚══════════════════════════════════════════════════╝

  MAIN MENU
  ──────────────────────────────────────────────────
  [1]  🎵  Search & play a Song
  [2]  💿  Search & play an Album
  [3]  📋  Search & play a Playlist
  [4]  🔗  Play from a URL (album/playlist)
  ──────────────────────────────────────────────────
  [0]  Quit
```

**Keyboard shortcuts during playback:**
- `Ctrl+C` — skip the current track (continues to next)
- `Ctrl+C` at the menu — quit the player

---

## Tech Stack

| Tool | Role |
|---|---|
| [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) | Search and browse YouTube Music |
| [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | Extract high-quality audio stream URLs |
| [`mpv`](https://mpv.io/) | Audio playback (no video, no GUI) |