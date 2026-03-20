"""Data models for music tracks"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Track:
    """Represents a single music track"""
    id: Optional[int]
    filepath: str
    title: str
    artist: str
    album: str
    genre: Optional[str]
    duration: Optional[int]  # seconds
    year: Optional[int]
    track_number: Optional[int]
    
    def to_dict(self):
        """Convert to dict for LLM context"""
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'genre': self.genre or 'Unknown',
            'year': self.year,
            'duration_minutes': round(self.duration / 60, 1) if self.duration else None
        }
