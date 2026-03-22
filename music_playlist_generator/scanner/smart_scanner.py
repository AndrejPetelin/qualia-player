"""Smart metadata scanner - combines folder structure parsing with ID3 tags"""

from pathlib import Path
from typing import Optional, Dict
import re
import mutagen
from mutagen.easyid3 import EasyID3
from database.models import Track

class SmartScanner:
    """
    Intelligent metadata extraction with fallback hierarchy:
    1. Parse folder structure (most reliable for year/album)
    2. Read ID3 tags (best for artist/title)
    3. Merge both intelligently
    """
    
    def __init__(self):
        pass
    
    def extract_metadata(self, filepath: Path) -> Optional[Track]:
        """Extract metadata using smart hierarchy"""
        
        # Phase 1: Parse folder structure
        path_data = self._parse_folder_structure(filepath)
        
        # Phase 2: Read ID3 tags
        tag_data = self._read_id3_tags(filepath)
        
        # Phase 3: Merge intelligently
        merged = self._merge_metadata(path_data, tag_data, filepath)
        
        if not merged:
            return None
        
        return Track(
            id=None,
            filepath=str(filepath),
            title=merged['title'],
            artist=merged['artist'],
            album=merged['album'],
            genre=merged.get('genre'),
            duration=merged.get('duration'),
            year=merged.get('year'),
            track_number=merged.get('track_number')
        )
    
    def _parse_folder_structure(self, filepath: Path) -> Dict:
        """Extract metadata from folder structure and filename"""
        
        data = {
            'artist': None,
            'album': None,
            'year': None,
            'title': None,
            'track_number': None
        }
        
        # Get folder names
        parent_folder = filepath.parent.name  # Album folder
        grandparent_folder = filepath.parent.parent.name  # Artist folder (maybe)
        filename = filepath.stem  # Filename without extension
        
        # Try to extract year and album from parent folder
        # Pattern 1: (YYYY) Album Name
        match = re.match(r'^\((\d{4})\)\s*(.+)$', parent_folder)
        if match:
            data['year'] = int(match.group(1))
            data['album'] = match.group(2).strip()
        
        # Pattern 2: [YYYY] Album Name
        if not data['year']:
            match = re.match(r'^\[(\d{4})\]\s*(.+)$', parent_folder)
            if match:
                data['year'] = int(match.group(1))
                data['album'] = match.group(2).strip()
        
        # Pattern 3: YYYY Album Name (year at start, no brackets)
        if not data['year']:
            match = re.match(r'^(\d{4})\s+(.+)$', parent_folder)
            if match:
                data['year'] = int(match.group(1))
                data['album'] = match.group(2).strip()
        
        # Pattern 4: Artist - YYYY - Album
        if not data['year']:
            match = re.match(r'^(.+?)\s*-\s*(\d{4})\s*-\s*(.+)$', parent_folder)
            if match:
                data['artist'] = match.group(1).strip()
                data['year'] = int(match.group(2))
                data['album'] = match.group(3).strip()
        
        # Pattern 5: Album (YYYY) or Album [YYYY] (year at end)
        if not data['year']:
            match = re.search(r'^(.+?)\s*[\(\[](\d{4})[\)\]]', parent_folder)
            if match:
                data['album'] = match.group(1).strip()
                data['year'] = int(match.group(2))
        
        # If no year/album extracted yet, use folder name as album
        if not data['album']:
            data['album'] = parent_folder
        
        # Try to get artist from grandparent folder (if not already set)
        if not data['artist']:
            # Check if grandparent looks like an artist name (not "Music" or drive letter)
            if grandparent_folder and grandparent_folder not in ['Music', 'music', 'Downloads']:
                # Strip common suffixes like "Discography", "Collection", etc.
                artist_name = grandparent_folder
                artist_name = re.sub(r'\s+(Discography|Collection|Complete|Albums)$', '', artist_name, flags=re.IGNORECASE)
                
                # Pattern: Artist - Album (YYYY)
                artist_match = re.match(r'^(.+?)\s*-\s*', artist_name)
                if artist_match:
                    data['artist'] = artist_match.group(1).strip()
                else:
                    data['artist'] = artist_name.strip()
        
        # Extract track number and title from filename
        # Pattern 1: 01 - Track Name
        match = re.match(r'^(\d+)\s*[-._]\s*(.+)$', filename)
        if match:
            data['track_number'] = int(match.group(1))
            data['title'] = match.group(2).strip()
        
        # Pattern 2: 01. Track Name
        if not data['track_number']:
            match = re.match(r'^(\d+)\.\s*(.+)$', filename)
            if match:
                data['track_number'] = int(match.group(1))
                data['title'] = match.group(2).strip()
        
        # Pattern 3: Track Name (no number)
        if not data['title']:
            data['title'] = filename
        
        return data
    
    def _read_id3_tags(self, filepath: Path) -> Dict:
        """Read metadata from ID3 tags"""
        
        data = {
            'artist': None,
            'album': None,
            'year': None,
            'title': None,
            'track_number': None,
            'genre': None,
            'duration': None
        }
        
        try:
            audio = mutagen.File(filepath, easy=True)
            if audio is None:
                return data
            
            # Helper to get first item from list
            def get_first(tag):
                val = audio.get(tag, [])
                return val[0] if val else None
            
            data['title'] = get_first('title')
            data['artist'] = get_first('artist')
            data['album'] = get_first('album')
            data['genre'] = get_first('genre')
            
            # Year
            date_str = get_first('date')
            if date_str:
                try:
                    # Extract year from various date formats
                    year_match = re.search(r'(\d{4})', date_str)
                    if year_match:
                        data['year'] = int(year_match.group(1))
                except:
                    pass
            
            # Track number
            track_str = get_first('tracknumber')
            if track_str:
                try:
                    # Handle "5/12" format (track 5 of 12)
                    track_num = track_str.split('/')[0]
                    data['track_number'] = int(track_num)
                except:
                    pass
            
            # Duration
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                data['duration'] = int(audio.info.length)
        
        except Exception as e:
            # If tag reading fails, return empty data (will use path data)
            pass
        
        return data
    
    def _merge_metadata(self, path_data: Dict, tag_data: Dict, filepath: Path) -> Optional[Dict]:
        """Merge path and tag data intelligently"""
        
        merged = {}
        
        # YEAR: Prefer path data (more reliable from folder names)
        merged['year'] = path_data.get('year') or tag_data.get('year')
        
        # ALBUM: Prefer path data (folder structure is cleaner)
        merged['album'] = path_data.get('album') or tag_data.get('album') or 'Unknown Album'
        
        # ARTIST: Prefer tag data (handles encoding better, e.g. Måneskin)
        # But fall back to path if tag is empty
        merged['artist'] = tag_data.get('artist') or path_data.get('artist') or 'Unknown Artist'
        
        # TITLE: Prefer tag data, fall back to filename
        merged['title'] = tag_data.get('title') or path_data.get('title') or filepath.stem
        
        # TRACK NUMBER: Prefer tag data, fall back to filename
        merged['track_number'] = tag_data.get('track_number') or path_data.get('track_number')
        
        # GENRE: Only from tags (not in folder structure)
        merged['genre'] = tag_data.get('genre')
        
        # DURATION: Only from tags
        merged['duration'] = tag_data.get('duration')
        
        return merged