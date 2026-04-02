# CLI Music Player

A minimalist, terminal-based YouTube Music player. It searches YouTube Music for studio tracks, extracts the highest-quality audio stream using `yt-dlp`, and plays it invisibly in the background using `mpv`. 

No bulky GUIs, no web browsers—just text and music.

## Prerequisites

This application requires `mpv` to be installed on your system to handle the background audio playback.

**For Arch Linux / CachyOS:**
```bash
sudo pacman -S mpv
```

## Setup

1. Clone the Repository:
    ```bash
    git clone https://github.com/Spring317/youtube-music-cli.git
    cd youtube-music-cli
    ```
2. Create and activate Conda Env.

    ```bash
    conda create -n cli-music python=3.11 -y
    conda activate cli-music
    ```
3. Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```
4. Compile into a Standalone Binary: 

    ```bash
    pyinstaller --onefile --collect-data ytmusicapi -n climusic src/climusic/main.py
    mkdir -p ~/.local/bin
    mv dist/climusic ~/.local/bin/
    climusic
    ```
## Usages
1. Type the name of a song/artist and hit Enter to start listen to music
   
## TODO

- Implement a google log-in for personalization
- Implement playlist/album search and play.