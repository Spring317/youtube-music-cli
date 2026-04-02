import subprocess
import sys
from ytmusicapi import YTMusic
import yt_dlp

def play_song(query):
    print(f"Searching for: '{query}'...")
    
    ytmusic = YTMusic()
    search_results = ytmusic.search(query, filter="songs") 
    
    if not search_results:
        print("No songs found. Try a different search.")
        return

    first_song = search_results[0]
    video_id = first_song['videoId']
    title = first_song['title']
    artists = ", ".join([artist['name'] for artist in first_song['artists']])
    
    print(f"\nFound: {title} by {artists}")
    print("Extracting audio stream...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True, 
        'noplaylist': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            stream_url = info['url']
    except Exception as e:
        print(f"Failed to extract stream: {e}")
        return

    print(f"\n▶ Playing: {title} by {artists} \n(Press Ctrl+C to stop)")
    try:
        subprocess.run(
            ['mpv', '--no-video', stream_url], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL  
        )
    except KeyboardInterrupt:
        print("\nPlayback stopped.")
    except FileNotFoundError:
         print("\nError: 'mpv' player not found on your system. Please install it.")

def main():
    print("Welcome to CLI Music Player!")
    while True:
        try:
            print("-" * 40)
            user_query = input("Enter a song to play (or press Ctrl+C to quit): ")
            if not user_query.strip():
                continue
            play_song(user_query)
        except KeyboardInterrupt:
            print("\nExiting player. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()
