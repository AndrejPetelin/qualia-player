#!/usr/bin/env python3
"""
Generate a simple artist list for testing
"""

import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from database.db_manager import MusicDatabase

def generate_artist_list():
    """Generate a simple text file with just artist names"""
    
    db = MusicDatabase(config.DB_PATH)
    tracks = db.get_all_tracks()
    
    # Get unique artists
    artists = sorted(set(track.artist for track in tracks))
    
    # Write to file
    output_file = Path.home() / "music_artists_list.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("ARTISTS IN MUSIC LIBRARY\n")
        f.write("=" * 40 + "\n\n")
        
        for artist in artists:
            f.write(f"{artist}\n")
        
        f.write(f"\n\nTotal: {len(artists)} artists")
    
    print(f"✅ Artist list written to: {output_file}")
    print(f"Total artists: {len(artists)}")

if __name__ == "__main__":
    generate_artist_list()