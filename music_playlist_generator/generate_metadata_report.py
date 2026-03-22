#!/usr/bin/env python3
"""
Generate a report of what's in the database
Shows quality of metadata extraction
"""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

import config
from database.db_manager import MusicDatabase

def generate_metadata_report():
    """Create a comprehensive metadata quality report"""
    
    db = MusicDatabase(config.DB_PATH)
    tracks = db.get_all_tracks()
    
    print(f"\n{'='*80}")
    print(f"QUALIA PLAYER - DATABASE METADATA REPORT")
    print(f"{'='*80}\n")
    
    print(f"Total tracks: {len(tracks)}")
    
    # Stats
    stats = {
        'has_year': 0,
        'has_genre': 0,
        'has_track_number': 0,
        'unknown_artist': 0,
        'unknown_album': 0
    }
    
    # Collect data
    artists = defaultdict(lambda: {
        'albums': set(),
        'track_count': 0,
        'has_year': 0,
        'missing_year': 0,
        'years': set()
    })
    
    albums_by_year = defaultdict(list)
    
    for track in tracks:
        # Stats
        if track.year:
            stats['has_year'] += 1
        if track.genre:
            stats['has_genre'] += 1
        if track.track_number:
            stats['has_track_number'] += 1
        if track.artist == 'Unknown Artist':
            stats['unknown_artist'] += 1
        if track.album == 'Unknown Album':
            stats['unknown_album'] += 1
        
        # Artist data
        artist = track.artist
        artists[artist]['track_count'] += 1
        artists[artist]['albums'].add(track.album)
        if track.year:
            artists[artist]['has_year'] += 1
            artists[artist]['years'].add(track.year)
        else:
            artists[artist]['missing_year'] += 1
        
        # Albums by year
        if track.year:
            albums_by_year[track.year].append(f"{track.artist} - {track.album}")
    
    # Print stats
    print(f"\nMETADATA COMPLETENESS:")
    print(f"  Tracks with year: {stats['has_year']} ({stats['has_year']/len(tracks)*100:.1f}%)")
    print(f"  Tracks with genre: {stats['has_genre']} ({stats['has_genre']/len(tracks)*100:.1f}%)")
    print(f"  Tracks with track number: {stats['has_track_number']} ({stats['has_track_number']/len(tracks)*100:.1f}%)")
    print(f"  Unknown artists: {stats['unknown_artist']}")
    print(f"  Unknown albums: {stats['unknown_album']}")
    
    # Top artists
    print(f"\n{'='*80}")
    print(f"TOP 20 ARTISTS BY TRACK COUNT:")
    print(f"{'='*80}\n")
    
    sorted_artists = sorted(artists.items(), key=lambda x: x[1]['track_count'], reverse=True)[:20]
    
    for artist, data in sorted_artists:
        year_coverage = f"{data['has_year']}/{data['track_count']}"
        year_range = ""
        if data['years']:
            year_range = f"({min(data['years'])}-{max(data['years'])})"
        
        print(f"{artist[:40]:40s} | {data['track_count']:4d} tracks | {len(data['albums']):3d} albums | Years: {year_coverage:8s} {year_range}")
    
    # Albums missing years
    print(f"\n{'='*80}")
    print(f"ARTISTS WITH MISSING YEAR DATA:")
    print(f"{'='*80}\n")
    
    artists_missing_years = [(artist, data) for artist, data in artists.items() if data['missing_year'] > 0]
    artists_missing_years.sort(key=lambda x: x[1]['missing_year'], reverse=True)
    
    for artist, data in artists_missing_years[:20]:
        print(f"{artist[:40]:40s} | {data['missing_year']:4d} tracks missing year data")
    
    # Chronological view
    print(f"\n{'='*80}")
    print(f"CHRONOLOGICAL VIEW (First 50 years):")
    print(f"{'='*80}\n")
    
    sorted_years = sorted(albums_by_year.keys())[:50]
    
    for year in sorted_years:
        albums = set(albums_by_year[year])  # Deduplicate
        print(f"\n{year}:")
        for album in sorted(albums)[:10]:  # Show max 10 per year
            print(f"  - {album}")
        if len(albums) > 10:
            print(f"  ... and {len(albums) - 10} more")
    
    # Write to file
    output_file = Path.home() / "qualia_metadata_report.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("QUALIA PLAYER - DETAILED ARTIST/ALBUM REPORT\n")
        f.write("="*80 + "\n\n")
        
        for artist in sorted(artists.keys()):
            data = artists[artist]
            f.write(f"\n{artist}\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total tracks: {data['track_count']}\n")
            f.write(f"Total albums: {len(data['albums'])}\n")
            f.write(f"Tracks with year: {data['has_year']}/{data['track_count']}\n")
            
            if data['years']:
                f.write(f"Year range: {min(data['years'])}-{max(data['years'])}\n")
            
            f.write(f"\nAlbums:\n")
            for album in sorted(data['albums']):
                f.write(f"  - {album}\n")
    
    print(f"\n{'='*80}")
    print(f"✅ Detailed report written to: {output_file}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    generate_metadata_report()