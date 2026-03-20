"""SQLite database operations"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from .models import Track

class MusicDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
    
    def _create_tables(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT UNIQUE NOT NULL,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    genre TEXT,
                    duration INTEGER,
                    year INTEGER,
                    track_number INTEGER,
                    last_modified REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_genre ON tracks(genre)")
    
    def add_track(self, track: Track) -> int:
        """Add or update a track in the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO tracks 
                (filepath, title, artist, album, genre, duration, year, track_number, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track.filepath, track.title, track.artist, track.album,
                track.genre, track.duration, track.year, track.track_number,
                Path(track.filepath).stat().st_mtime
            ))
            return cursor.lastrowid
    
    def get_all_tracks(self) -> List[Track]:
        """Retrieve all tracks from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM tracks").fetchall()
            return [Track(
                id=row['id'],
                filepath=row['filepath'],
                title=row['title'],
                artist=row['artist'],
                album=row['album'],
                genre=row['genre'],
                duration=row['duration'],
                year=row['year'],
                track_number=row['track_number']
            ) for row in rows]
    
    def get_track_count(self) -> int:
        """Get total number of tracks"""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    
    def remove_track(self, filepath: str):
        """Remove a track from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tracks WHERE filepath = ?", (filepath,))
