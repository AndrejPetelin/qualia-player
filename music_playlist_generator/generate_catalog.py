#!/usr/bin/env python3
"""
Generate a library catalog file for testing with chat
"""

import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from database.db_manager import MusicDatabase
from collections import defaultdict

def generate_catalog_file():
    """Generate a text file with artist catalog"""
    
    db = MusicDatabase(config.DB_PATH)
    tracks = db.get_all_tracks()
    
    # Build artist catalog
    catalog = defaultdict(lambda: {
        'genres': set(),
        'track_count': 0,
        'albums': set(),
        'sample_titles': []
    })
    
    for track in tracks:
        artist = track.artist
        genre = track.genre or 'Unknown'
        album = track.album or 'Unknown'
        title = track.title
        
        catalog[artist]['genres'].add(genre)
        catalog[artist]['track_count'] += 1
        catalog[artist]['albums'].add(album)
        
        if len(catalog[artist]['sample_titles']) < 5:
            catalog[artist]['sample_titles'].append(title)
    
    # Write to file
    output_file = Path.home() / "music_library_catalog.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("MUSIC LIBRARY CATALOG\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total tracks: {len(tracks)}\n")
        f.write(f"Total artists: {len(catalog)}\n\n")
        f.write("=" * 80 + "\n\n")
        
        for artist in sorted(catalog.keys()):
            info = catalog[artist]
            
            f.write(f"\n{artist}\n")
            f.write("-" * 60 + "\n")
            f.write(f"Tracks: {info['track_count']}\n")
            f.write(f"Genres: {', '.join(sorted(info['genres']))}\n")
            f.write(f"Albums: {', '.join(sorted(info['albums']))}\n")
            f.write(f"Sample tracks: {', '.join(info['sample_titles'])}\n")
    
    print(f"✅ Catalog written to: {output_file}")
    print(f"\nTotal artists: {len(catalog)}")
    print(f"Total tracks: {len(tracks)}")

if __name__ == "__main__":
    generate_catalog_file()