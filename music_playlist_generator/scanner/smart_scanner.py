"""Smart metadata scanner - two-pass strategy with intelligent heuristics"""

from pathlib import Path
from typing import Optional, Dict, List, Tuple
import re
import mutagen
from database.models import Track

class SmartScanner:
    """
    Intelligent two-pass metadata extraction:
    
    Pass 1: Folder structure (fast, reliable for organized files) 
    Pass 2: ID3 tags (fallback for missing/suspicious folder data)
    """
    
    # Audio file extensions we recognize
    AUDIO_EXTENSIONS = {'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus'}
    
    def __init__(self):
        self.pass_1_success = []
        self.pass_1_failed = []
        self.pass_2_success = []
        self.pass_2_failed = []
    
    def scan_with_three_passes(self, audio_files: List[Path], progress_callback=None) -> Tuple[List[Track], List[Dict]]:
        """
        Two-pass scanning strategy:
        1. Try folder structure (skip if artist looks suspicious)
        2. Try ID3 tags for everything that failed Pass 1
        """
        
        total = len(audio_files)
        
        # PASS 1: Folder structure only
        print("\n" + "="*80)
        print("PASS 1: Extracting from folder structure...")
        print("="*80)
        
        for i, filepath in enumerate(audio_files, 1):
            if progress_callback:
                progress_callback(i, total, f"Pass 1: {filepath.name}")
            
            path_data = self._parse_folder_structure(filepath)
            
            # Check if artist looks suspicious
            artist_suspicious = self._is_suspicious_artist(path_data.get('artist'))
            
            # Success criteria: Has artist AND album AND artist doesn't look broken
            if self._is_complete_metadata(path_data) and not artist_suspicious:
                track = self._create_track(filepath, path_data, skip_tags=True)
                self.pass_1_success.append(track)
            else:
                if artist_suspicious:
                    print(f"  ⚠️  Suspicious artist '{path_data.get('artist')}': {filepath.name}")
                self.pass_1_failed.append(filepath)
        
        print(f"\n✅ Pass 1: {len(self.pass_1_success)} tracks extracted from folders")
        print(f"⏭️  Pass 1: {len(self.pass_1_failed)} tracks need tag fallback")
        
        # PASS 2: ID3 tags for failed files
        if self.pass_1_failed:
            print("\n" + "="*80)
            print("PASS 2: Reading ID3 tags for remaining files...")
            print("="*80)
            
            for i, filepath in enumerate(self.pass_1_failed, 1):
                if progress_callback:
                    progress_callback(i, len(self.pass_1_failed), f"Pass 2: {filepath.name}")
                
                path_data = self._parse_folder_structure(filepath)
                tag_data = self._read_id3_tags(filepath)
                
                # Check for garbage BEFORE merging
                garbage_warnings = self._detect_garbage_metadata(
                    tag_data.get('artist') or '',
                    tag_data.get('album') or '',
                    tag_data.get('title') or ''
                )
                
                if garbage_warnings:
                    # Tags are garbage, mark as failed
                    print(f"  ⚠️  Garbage tags: {filepath.name}")
                    self.pass_2_failed.append({
                        'filepath': filepath,
                        'path_data': path_data,
                        'tag_data': tag_data,
                        'warnings': garbage_warnings
                    })
                else:
                    # Merge and check if now complete
                    merged = self._merge_metadata(path_data, tag_data, filepath)
                    
                    if self._is_complete_metadata(merged):
                        track = self._create_track(filepath, merged)
                        self.pass_2_success.append(track)
                    else:
                        self.pass_2_failed.append({
                            'filepath': filepath,
                            'path_data': path_data,
                            'tag_data': tag_data,
                            'warnings': {}
                        })
            
            print(f"\n✅ Pass 2: {len(self.pass_2_success)} tracks extracted from tags")
            print(f"❌ Pass 2: {len(self.pass_2_failed)} tracks failed")
        
        # Combine all successful tracks
        all_tracks = self.pass_1_success + self.pass_2_success
        
        return all_tracks, self.pass_2_failed
    
    def _is_suspicious_artist(self, artist: Optional[str]) -> bool:
        """
        Detect if extracted artist name looks broken.
        A real band name should be mostly letters (and spaces).
        Anything with numbers or weird punctuation → suspicious!
        """
        if not artist:
            return True
        
        artist = artist.strip()
        
        # Remove spaces to check the rest
        artist_no_spaces = artist.replace(' ', '')
        
        # If what's left is NOT all letters → suspicious!
        # This catches:
        # - "1989" (numbers)
        # - "[Compilations]" (brackets)
        # - "Deep Purple - 1972 - Live" (dashes + numbers)
        # - "Lana Del Rey - Discography (2012-2021)" (parens + numbers)
        # - "1974-2014 Rob Halford" (numbers + dashes)
        # - "Aretha Franklin-Greatest Hits (mp3) {tre123wor}" (chaos!)
        if not artist_no_spaces.isalpha():
            return True
        
        return False
    
    def _is_complete_metadata(self, data: Dict) -> bool:
        """Check if metadata is complete enough to use"""
        
        # Must have artist AND album
        has_artist = data.get('artist') and data['artist'] not in ['Unknown Artist', '', None]
        has_album = data.get('album') and data['album'] not in ['Unknown Album', '', None]
        
        # Title is less critical (we can use filename)
        has_title = data.get('title') and data['title'] not in ['', None]
        
        return has_artist and has_album and has_title
    
    def _create_track(self, filepath: Path, data: Dict, skip_tags: bool = False) -> Track:
        """Create a Track object from metadata dict"""
        
        duration = data.get('duration')
        genre = data.get('genre')
        
        # ALWAYS read genre and duration from tags
        # Genre is only in ID3 tags, not in folder structure
        # Duration is also only in tags
        if not genre or not duration:
            tag_data = self._read_id3_tags(filepath)
            if not genre:
                genre = tag_data.get('genre')
            if not duration:
                duration = tag_data.get('duration')
        
        return Track(
            id=None,
            filepath=str(filepath),
            title=data.get('title') or filepath.stem,
            artist=data.get('artist') or 'Unknown Artist',
            album=data.get('album') or 'Unknown Album',
            genre=genre,
            duration=duration,
            year=data.get('year'),
            track_number=data.get('track_number')
        )
    
    def _is_disc_or_format_folder(self, folder_name: str) -> bool:
        """
        Detect if this folder is a disc subfolder (CD1, Disc 2) 
        or format subfolder (mp3, flac)
        """
        folder_lower = folder_name.lower()
        
        # Disc folders: CD1, CD2, Disc 1, Disc 2, Disk 1, etc.
        if re.match(r'^(cd|disc|disk)\s*\d+$', folder_lower):
            return True
        
        # Format folders: mp3, flac, wav, etc.
        if folder_lower in ['mp3', 'flac', 'wav', 'ogg', 'm4a', 'aac', 'opus', 'wma']:
            return True
        
        return False
    
    def _extract_year_from_text(self, text: str) -> Optional[int]:
        """
        Extract year (19xx or 20xx) from any text.
        Simple and robust - if it has 4 digits starting with 19 or 20, it's a year!
        """
        year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if year_matches:
            return int(year_matches[0])  # Return first match
        return None
    
    def _clean_album_name(self, album_text: str, year: Optional[int] = None) -> str:
        """Remove year and common decorations from album name"""
        cleaned = album_text
        
        # Remove the year if we found one
        if year:
            cleaned = re.sub(rf'\s*[\(\[]?{year}[\)\]]?\s*', ' ', cleaned)
        
        # Remove any remaining year-like patterns
        cleaned = re.sub(r'\s*[\(\[]?(19\d{2}|20\d{2})[\)\]]?\s*', ' ', cleaned)
        
        # Remove common decorations
        cleaned = re.sub(r'\s*[\(\[].*?(remaster|deluxe|edition|bonus|expanded).*?[\)\]]', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _parse_folder_structure(self, filepath: Path) -> Dict:
        """
        Parse folder structure using depth detection.
        
        The folder containing the audio file is either:
        - The album folder directly, OR
        - A disc/format subfolder, in which case album is one level up
        """
        
        data = {
            'artist': None,
            'album': None,
            'year': None,
            'title': None,
            'track_number': None
        }
        
        # Get the folder containing this audio file
        immediate_parent = filepath.parent.name
        
        # Check if it's a disc or format folder
        if self._is_disc_or_format_folder(immediate_parent):
            # Real album is one level up
            album_folder = filepath.parent.parent.name
            artist_folder = filepath.parent.parent.parent.name if len(list(filepath.parents)) > 2 else None
            parent_path = filepath.parent.parent.parent
        else:
            # This IS the album folder
            album_folder = immediate_parent
            artist_folder = filepath.parent.parent.name if len(list(filepath.parents)) > 1 else None
            parent_path = filepath.parent.parent
        
        # Check if artist_folder is actually a collection root (like "Glasba" or "Music")
        # by counting subfolders
        is_collection_root = False
        if parent_path and parent_path.exists():
            try:
                subfolders = [f for f in parent_path.iterdir() if f.is_dir()]
                is_collection_root = len(subfolders) >= 10
            except:
                pass
        
        if is_collection_root:
            # Artist folder is probably "Music" or "Glasba"
            # Try to extract artist from album folder name instead
            
            # CRITICAL: Check if folder starts with YEAR first!
            # Pattern: "1967 - The Piper At The Gates Of Dawn"
            year_first = re.match(r'^(19\d{2}|20\d{2})\s*-\s*(.+)$', album_folder)
            
            if year_first:
                # Year comes first - use grandparent as artist
                data['year'] = int(year_first.group(1))
                data['album'] = self._clean_album_name(year_first.group(2), data['year'])
                
                # Clean grandparent folder name for artist
                if artist_folder:
                    artist_name = artist_folder
                    # Remove common discography suffixes (including non-English)
                    artist_name = re.sub(r'\s*-?\s*(Discography|Diskografija|Discografia|Collection|Complete|Albums|STUDIO DISCOGRAPHY|Studio Albums).*$', '', artist_name, flags=re.IGNORECASE)
                    # Remove [CHANNEL NEO] style tags
                    artist_name = re.sub(r'\s*\[.*?\]\s*$', '', artist_name)
                    data['artist'] = artist_name.strip()
            else:
                # Pattern: "Artist - Album" or "Artist - Year - Album"
                artist_match = re.match(r'^(.+?)\s*-\s*(?:(19\d{2}|20\d{2})\s*-\s*)?(.+)$', album_folder)
                if artist_match:
                    data['artist'] = artist_match.group(1).strip()
                    # Extract year if present in middle position
                    if artist_match.group(2):
                        data['year'] = int(artist_match.group(2))
                    # Album is the last part
                    album_text = artist_match.group(3).strip()
                    # Still try to extract year from album text if not found yet
                    if not data['year']:
                        data['year'] = self._extract_year_from_text(album_text)
                    data['album'] = self._clean_album_name(album_text, data['year'])
                else:
                    # Couldn't parse with dashes, try extracting year from anywhere
                    data['year'] = self._extract_year_from_text(album_folder)
                    data['album'] = self._clean_album_name(album_folder, data['year'])
        else:
            # Normal artist folder structure
            # Extract year from album folder
            data['year'] = self._extract_year_from_text(album_folder)
            
            # Clean album name
            data['album'] = self._clean_album_name(album_folder, data['year'])
            
            # Extract artist from artist folder
            if artist_folder:
                # Clean up common suffixes
                artist_name = artist_folder
                artist_name = re.sub(r'\s+(Discography|Collection|Complete|Albums)$', '', artist_name, flags=re.IGNORECASE)
                data['artist'] = artist_name.strip()
        
        # Extract track number and title from filename
        filename = filepath.stem
        
        # Pattern: "01 - Track Name" or "01. Track Name" or "01 Track Name"
        track_match = re.match(r'^(\d+)\s*[-._]?\s*(.+)$', filename)
        if track_match:
            data['track_number'] = int(track_match.group(1))
            data['title'] = track_match.group(2).strip()
        else:
            # No track number, just use filename as title
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
                # Extract any 19xx or 20xx year
                data['year'] = self._extract_year_from_text(date_str)
            
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
            # If tag reading fails, return empty data
            pass
        
        return data
    
    def _detect_garbage_metadata(self, artist: str, album: str, title: str) -> Dict[str, str]:
        """
        Detect OBVIOUSLY garbage metadata.
        Conservative approach - only flag truly egregious stuff.
        """
        
        warnings = {}
        
        # ONLY flag website URLs - this is unambiguous
        url_pattern = r'\b(www\.|http|\.com|\.net|\.org|\.co\.|\.fm|\.io|\.eg)\b'
        
        if re.search(url_pattern, artist, re.IGNORECASE):
            warnings['artist'] = f"Website URL in artist: '{artist}'"
        
        if re.search(url_pattern, album, re.IGNORECASE):
            warnings['album'] = f"Website URL in album: '{album}'"
        
        # ONLY flag uploader signatures with capital "By" at the end
        # "By SmSma" ✓, "by Clouds" ✗
        if re.search(r'\s+By\s+[A-Z]\w+$', album):
            warnings['album'] = f"Uploader signature in album: '{album}'"
        
        # Same value in ALL three fields = possible spam
        # BUT: Could be self-titled track (e.g., Tin Machine - Tin Machine - Tin Machine)
        # Only flag if it contains website indicators
        if artist == album == title and len(artist) < 30 and artist.strip():
            # Check if it contains website indicators
            if re.search(r'\.(com|net|org|www|co\.)', artist, re.IGNORECASE):
                warnings['all_fields'] = f"Same spam value everywhere: '{artist}'"
            # Otherwise let it pass - could be legitimate self-titled track
        
        return warnings
    
    def _merge_metadata(self, path_data: Dict, tag_data: Dict, filepath: Path) -> Dict:
        """
        Merge path and tag data intelligently.
        
        Priority:
        - YEAR: path > tags (folder structure more reliable)
        - ALBUM: path > tags (folder structure cleaner)
        - ARTIST: tags > path (handles encoding better, e.g., Måneskin)
        - TITLE: tags > path (proper capitalization)
        - TRACK NUMBER: tags > path (more reliable)
        """
        
        merged = {}
        
        # YEAR: Prefer path data
        merged['year'] = path_data.get('year') or tag_data.get('year')
        
        # ALBUM: Prefer path data (cleaner folder names)
        merged['album'] = path_data.get('album') or tag_data.get('album')
        
        # ARTIST: Prefer tag data (handles encoding better)
        # But fall back to path if tag is empty
        merged['artist'] = tag_data.get('artist') or path_data.get('artist')
        
        # TITLE: Prefer tag data (proper capitalization)
        merged['title'] = tag_data.get('title') or path_data.get('title')
        
        # TRACK NUMBER: Prefer tag data
        merged['track_number'] = tag_data.get('track_number') or path_data.get('track_number')
        
        # GENRE: Only from tags (not in folder structure)
        merged['genre'] = tag_data.get('genre')
        
        # DURATION: Only from tags
        merged['duration'] = tag_data.get('duration')
        
        return merged
