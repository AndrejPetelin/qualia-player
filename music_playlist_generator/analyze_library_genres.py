#!/usr/bin/env python3
"""
Analyze library and build a genre map
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

import config
from database.db_manager import MusicDatabase
from collections import defaultdict

def analyze_library_genres():
    """Build a genre taxonomy from the actual library"""
    
    db = MusicDatabase(config.DB_PATH)
    tracks = db.get_all_tracks()
    
    # Collect all unique genres and their artists
    genre_data = defaultdict(lambda: {
        'track_count': 0,
        'artists': set()
    })
    
    for track in tracks:
        genre = track.genre or 'Unknown'
        genre_data[genre]['track_count'] += 1
        genre_data[genre]['artists'].add(track.artist)
    
    # Convert sets to lists for JSON
    genre_map = {}
    for genre, data in genre_data.items():
        genre_map[genre] = {
            'track_count': data['track_count'],
            'artist_count': len(data['artists']),
            'artists': sorted(data['artists'])
        }
    
    # Save to config file
    output_file = Path(__file__).parent / "genre_map.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(genre_map, f, indent=2, ensure_ascii=False)
    
    # Also print summary
    print("\n" + "=" * 60)
    print("GENRE ANALYSIS")
    print("=" * 60)
    
    sorted_genres = sorted(genre_map.items(), key=lambda x: -x[1]['track_count'])
    
    for genre, data in sorted_genres:
        print(f"\n{genre}:")
        print(f"  Tracks: {data['track_count']}")
        print(f"  Artists: {data['artist_count']}")
        print(f"  Example artists: {', '.join(data['artists'][:5])}")
    
    print(f"\n✅ Genre map saved to: {output_file}")
    print(f"Total unique genres: {len(genre_map)}")

if __name__ == "__main__":
    analyze_library_genres()