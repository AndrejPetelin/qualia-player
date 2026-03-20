"""Music library scanning with metadata extraction"""

from pathlib import Path
from typing import List, Callable, Optional
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Track

class MusicScanner:
    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Args:
            progress_callback: Function called with (current, total, filepath) during scan
        """
        self.progress_callback = progress_callback
    
    def scan_folder(self, folder: Path, extensions: set) -> List[Track]:
        """Recursively scan folder for audio files and extract metadata"""
        tracks = []
        audio_files = []
        
        # First, collect all audio files
        for ext in extensions:
            audio_files.extend(folder.rglob(f"*{ext}"))
        
        total = len(audio_files)
        
        for i, filepath in enumerate(audio_files, 1):
            if self.progress_callback:
                self.progress_callback(i, total, str(filepath))
            
            track = self._extract_metadata(filepath)
            if track:
                tracks.append(track)
        
        return tracks
    
    def _extract_metadata(self, filepath: Path) -> Optional[Track]:
        """Extract metadata from a single audio file"""
        try:
            audio = mutagen.File(filepath, easy=True)
            if audio is None:
                return None
            
            # Helper to get first item from list or None
            def get_first(tag):
                val = audio.get(tag, [])
                return val[0] if val else None
            
            return Track(
                id=None,
                filepath=str(filepath),
                title=get_first('title') or filepath.stem,
                artist=get_first('artist') or 'Unknown Artist',
                album=get_first('album') or 'Unknown Album',
                genre=get_first('genre'),
                duration=int(audio.info.length) if hasattr(audio, 'info') else None,
                year=int(get_first('date')[:4]) if get_first('date') else None,
                track_number=int(get_first('tracknumber').split('/')[0]) if get_first('tracknumber') else None
            )
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None
