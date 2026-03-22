"""Track filtering system for complex playlist requests"""

from typing import List, Dict, Set
from collections import defaultdict
import re

class TrackFilter:
    """Handles complex track filtering based on user requests"""
    
    def __init__(self, user_request: str):
        self.request = user_request.lower()
        self.filters = self._detect_filters()
    
    def _detect_filters(self) -> Dict:
        """Detect what filters the user wants"""
        filters = {
            'year_range': None,
            'decade': None,
            'one_per_album': False,
            'chronological': False,
            'live_only': False,
            'studio_only': False,
            'min_duration': None,
            'max_duration': None,
            'specific_artists': []
        }
        
        # Year range detection
        year_match = re.search(r'(\d{4})\s*-\s*(\d{4})', self.request)
        if year_match:
            filters['year_range'] = (int(year_match.group(1)), int(year_match.group(2)))
        
        # Decade detection
        if '80s' in self.request or 'eighties' in self.request:
            filters['decade'] = (1980, 1989)
        elif '90s' in self.request or 'nineties' in self.request:
            filters['decade'] = (1990, 1999)
        elif '70s' in self.request or 'seventies' in self.request:
            filters['decade'] = (1970, 1979)
        elif '2000s' in self.request:
            filters['decade'] = (2000, 2009)
        
        # "After/before year X"
        after_match = re.search(r'after\s+(\d{4})', self.request)
        if after_match:
            filters['year_range'] = (int(after_match.group(1)), 2030)
        
        before_match = re.search(r'before\s+(\d{4})', self.request)
        if before_match:
            filters['year_range'] = (1950, int(before_match.group(1)))
        
        # Album-based
        if 'one per album' in self.request or 'per album' in self.request or 'each album' in self.request:
            filters['one_per_album'] = True
        
        # Chronological
        if 'chronological' in self.request or 'chronologically' in self.request or 'in order' in self.request:
            filters['chronological'] = True
        
        # Live vs Studio
        if 'live' in self.request and 'studio' not in self.request:
            filters['live_only'] = True
        elif 'studio' in self.request and 'live' not in self.request:
            filters['studio_only'] = True
        
        # Duration
        if 'over' in self.request or 'longer than' in self.request:
            duration_match = re.search(r'over\s+(\d+)\s*min', self.request)
            if duration_match:
                filters['min_duration'] = int(duration_match.group(1)) * 60
        
        if 'under' in self.request or 'shorter than' in self.request:
            duration_match = re.search(r'under\s+(\d+)\s*min', self.request)
            if duration_match:
                filters['max_duration'] = int(duration_match.group(1)) * 60
        
        return filters
    
    def apply(self, tracks: List[Dict]) -> List[Dict]:
        """Apply all detected filters to track list"""
        
        filtered = tracks
        
        # Year filtering
        if self.filters['year_range']:
            filtered = self._filter_by_year(filtered, *self.filters['year_range'])
        elif self.filters['decade']:
            filtered = self._filter_by_year(filtered, *self.filters['decade'])
        
        # Live/Studio filtering
        if self.filters['live_only']:
            filtered = self._filter_live_only(filtered)
        elif self.filters['studio_only']:
            filtered = self._filter_studio_only(filtered)
        
        # Duration filtering
        if self.filters['min_duration']:
            filtered = [t for t in filtered if (t.get('duration_minutes') or 0) * 60 >= self.filters['min_duration']]
        
        if self.filters['max_duration']:
            filtered = [t for t in filtered if (t.get('duration_minutes') or 0) * 60 <= self.filters['max_duration']]
        
        # Album-based filtering (one per album)
        if self.filters['one_per_album']:
            filtered = self._one_per_album(filtered)
        
        # Chronological sorting
        if self.filters['chronological']:
            filtered = self._sort_chronologically(filtered)
        
        return filtered
    
    def _filter_by_year(self, tracks: List[Dict], start_year: int, end_year: int) -> List[Dict]:
        """Filter tracks by year range"""
        filtered = []
        for track in tracks:
            year = track.get('year')
            if year and start_year <= year <= end_year:
                filtered.append(track)
        
        # If we filtered out EVERYTHING, return original (metadata probably missing)
        if not filtered and tracks:
            print(f"⚠️  Year filter ({start_year}-{end_year}) removed all tracks - metadata might be missing. Ignoring year filter.")
            return tracks
        
        return filtered
    
    def _filter_live_only(self, tracks: List[Dict]) -> List[Dict]:
        """Filter to only live recordings"""
        # Check album name for "live" indicators
        live_tracks = []
        for track in tracks:
            album = (track.get('album') or '').lower()
            title = (track.get('title') or '').lower()
            
            if 'live' in album or 'live' in title or 'concert' in album:
                live_tracks.append(track)
        
        if not live_tracks and tracks:
            print("⚠️  No live tracks detected (checking album/title for 'live'). Returning all tracks.")
            return tracks
        
        return live_tracks
    
    def _filter_studio_only(self, tracks: List[Dict]) -> List[Dict]:
        """Filter to only studio recordings (exclude live)"""
        studio_tracks = []
        for track in tracks:
            album = (track.get('album') or '').lower()
            title = (track.get('title') or '').lower()
            
            if 'live' not in album and 'live' not in title and 'concert' not in album:
                studio_tracks.append(track)
        
        return studio_tracks
    
    def _normalize_album_name(self, album: str) -> str:
        """Normalize album name to handle encoding issues and disc numbers"""
        import unicodedata
        
        # Remove non-ASCII characters (encoding garbage)
        normalized = ''.join(
            char for char in album 
            if ord(char) < 128 or char.isalnum() or char in ' ,-()[]'
        )
        
        # Remove disc/CD numbers at the end (CD1, CD 1, Disc 1, Disc 2, etc.)
        normalized = re.sub(r'\s*(cd|disc)\s*\d+\s*$', '', normalized, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()

    def _one_per_album(self, tracks: List[Dict]) -> List[Dict]:
        """Pick one random track per album"""
        import random
        
        albums = defaultdict(list)
        for track in tracks:
            album = track.get('album') or 'Unknown Album'
            # Normalize the album name to handle encoding issues
            normalized = self._normalize_album_name(album)
            albums[normalized].append(track)
        
        # DEBUG
        print(f"\n📀 One per album - found {len(albums)} unique albums (after normalization):")
        for album in sorted(albums.keys()):
            print(f"   {album}: {len(albums[album])} tracks")
        
        # Pick one random track from each album
        result = []
        for album, album_tracks in albums.items():
            result.append(random.choice(album_tracks))
        
        print(f"📀 Returning {len(result)} tracks (one per album)\n")
        
        return result
    
    def _sort_chronologically(self, tracks: List[Dict]) -> List[Dict]:
        """Sort tracks chronologically by year/album"""
        # Sort by: year (if available), then album, then track number
        def sort_key(track):
            year = track.get('year') or 9999
            album = track.get('album') or 'ZZZZ'
            track_num = track.get('track_number') or 0
            return (year, album, track_num)
        
        return sorted(tracks, key=sort_key)
    
    def needs_python_enforcement(self) -> bool:
        """Check if this request needs strict Python enforcement (skip 2nd Mistral call)"""
        return (
            self.filters['one_per_album'] or 
            self.filters['chronological'] or
            self.filters['year_range'] is not None or
            self.filters['decade'] is not None
        )