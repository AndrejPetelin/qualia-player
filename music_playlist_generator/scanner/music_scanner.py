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
from scanner.smart_scanner import SmartScanner

class MusicScanner:
    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Args:
            progress_callback: Function called with (current, total, filepath) during scan
        """
        self.progress_callback = progress_callback
        self.smart_scanner = SmartScanner()  # Use smart scanner instead of direct mutagen
    
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
            
            # Use smart scanner instead of old method
            track = self.smart_scanner.extract_metadata(filepath)
            if track:
                tracks.append(track)
        
        return tracks
    
    # Remove the old _extract_metadata method - we're using SmartScanner now
