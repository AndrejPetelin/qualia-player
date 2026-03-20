#!/usr/bin/env python3
"""
Bootstrap script for Music Playlist Generator
Creates the complete project structure with all files
"""

import os
from pathlib import Path

def create_project_structure():
    """Create all folders and files for the music playlist generator"""
    
    # Define project structure
    project_name = "music_playlist_generator"
    
    structure = {
        project_name: {
            "__init__.py": "",
            "main.py": MAIN_PY,
            "config.py": CONFIG_PY,
            "requirements.txt": REQUIREMENTS_TXT,
            "README.md": README_MD,
            "database": {
                "__init__.py": "",
                "db_manager.py": DB_MANAGER_PY,
                "models.py": MODELS_PY,
            },
            "scanner": {
                "__init__.py": "",
                "music_scanner.py": MUSIC_SCANNER_PY,
                "folder_monitor.py": FOLDER_MONITOR_PY,
            },
            "llm": {
                "__init__.py": "",
                "ollama_client.py": OLLAMA_CLIENT_PY,
            },
            "playlist": {
                "__init__.py": "",
                "generator.py": GENERATOR_PY,
            },
            "ui": {
                "__init__.py": "",
                "chat_window.py": CHAT_WINDOW_PY,
            },
        }
    }
    
    def create_structure(base_path, structure_dict):
        """Recursively create folders and files"""
        for name, content in structure_dict.items():
            path = base_path / name
            
            if isinstance(content, dict):
                # It's a directory
                path.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created directory: {path}")
                create_structure(path, content)
            else:
                # It's a file
                path.write_text(content, encoding='utf-8')
                print(f"📄 Created file: {path}")
    
    # Create the structure
    base_path = Path.cwd()
    create_structure(base_path, structure)
    
    print("\n✅ Project structure created successfully!")
    print(f"\n📍 Project location: {base_path / project_name}")
    print(f"\n🚀 Next steps:")
    print(f"   cd {project_name}")
    print(f"   pip install -r requirements.txt")
    print(f"   python main.py")


# ============================================
# FILE CONTENTS
# ============================================

REQUIREMENTS_TXT = """mutagen>=1.47.0
watchdog>=3.0.0
requests>=2.31.0
"""

README_MD = """# Music Playlist Generator

AI-powered playlist generator using local LLM (Ollama) and your music library.

## Features

- 🎵 Scans your local music library
- 🤖 Uses Ollama/Mistral to understand your playlist requests
- 💬 Chat interface to describe what you want
- 📝 Generates M3U playlists
- 👀 Monitors music folder for changes

## Installation
```bash
pip install -r requirements.txt
```

Make sure Ollama is running:
```bash
ollama serve
```

## Usage
```bash
python main.py
```

1. Select your music folder
2. Wait for library scan
3. Chat with the AI: "Make me a chill indie playlist, about 45 minutes"
4. Get your M3U playlist!

## Configuration

Edit `config.py` to change:
- Music folder location
- Ollama model
- Output folder for playlists

## Project Structure
```
music_playlist_generator/
├── main.py              # Entry point
├── config.py            # Configuration
├── database/            # SQLite operations
├── scanner/             # Music scanning & monitoring
├── llm/                 # Ollama integration
├── playlist/            # M3U generation
└── ui/                  # Tkinter interface
```
"""

CONFIG_PY = """\"\"\"Configuration settings for Music Playlist Generator\"\"\"

import os
from pathlib import Path

# Database
DB_PATH = Path.home() / ".music_playlist_generator" / "library.db"

# Music folder (can be changed by user)
MUSIC_FOLDER = Path.home() / "Music"

# Supported audio formats
AUDIO_EXTENSIONS = {'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus'}

# Ollama settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral"  # Change to whatever model you have

# Playlist output folder
PLAYLIST_OUTPUT = Path.home() / "Music" / "Playlists"
"""

MODELS_PY = """\"\"\"Data models for music tracks\"\"\"

from dataclasses import dataclass
from typing import Optional

@dataclass
class Track:
    \"\"\"Represents a single music track\"\"\"
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
        \"\"\"Convert to dict for LLM context\"\"\"
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'genre': self.genre or 'Unknown',
            'year': self.year,
            'duration_minutes': round(self.duration / 60, 1) if self.duration else None
        }
"""

DB_MANAGER_PY = """\"\"\"SQLite database operations\"\"\"

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
        \"\"\"Initialize database schema\"\"\"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(\"\"\"
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
            \"\"\")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_genre ON tracks(genre)")
    
    def add_track(self, track: Track) -> int:
        \"\"\"Add or update a track in the database\"\"\"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(\"\"\"
                INSERT OR REPLACE INTO tracks 
                (filepath, title, artist, album, genre, duration, year, track_number, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            \"\"\", (
                track.filepath, track.title, track.artist, track.album,
                track.genre, track.duration, track.year, track.track_number,
                Path(track.filepath).stat().st_mtime
            ))
            return cursor.lastrowid
    
    def get_all_tracks(self) -> List[Track]:
        \"\"\"Retrieve all tracks from database\"\"\"
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
        \"\"\"Get total number of tracks\"\"\"
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    
    def remove_track(self, filepath: str):
        \"\"\"Remove a track from database\"\"\"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tracks WHERE filepath = ?", (filepath,))
"""

MUSIC_SCANNER_PY = """\"\"\"Music library scanning with metadata extraction\"\"\"

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
        \"\"\"
        Args:
            progress_callback: Function called with (current, total, filepath) during scan
        \"\"\"
        self.progress_callback = progress_callback
    
    def scan_folder(self, folder: Path, extensions: set) -> List[Track]:
        \"\"\"Recursively scan folder for audio files and extract metadata\"\"\"
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
        \"\"\"Extract metadata from a single audio file\"\"\"
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
"""

FOLDER_MONITOR_PY = """\"\"\"Filesystem monitoring for music library changes\"\"\"

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable
import time

class MusicFolderHandler(FileSystemEventHandler):
    def __init__(self, audio_extensions: set, change_callback: Callable):
        \"\"\"
        Args:
            audio_extensions: Set of valid audio file extensions
            change_callback: Function to call when changes detected
        \"\"\"
        self.audio_extensions = audio_extensions
        self.change_callback = change_callback
        self.last_change_time = 0
        self.debounce_seconds = 3
    
    def _is_audio_file(self, path: str) -> bool:
        return Path(path).suffix.lower() in self.audio_extensions
    
    def _trigger_change(self):
        \"\"\"Debounced change notification\"\"\"
        current_time = time.time()
        if current_time - self.last_change_time > self.debounce_seconds:
            self.last_change_time = current_time
            self.change_callback()
    
    def on_created(self, event):
        if not event.is_directory and self._is_audio_file(event.src_path):
            self._trigger_change()
    
    def on_deleted(self, event):
        if not event.is_directory and self._is_audio_file(event.src_path):
            self._trigger_change()
    
    def on_moved(self, event):
        if not event.is_directory and self._is_audio_file(event.dest_path):
            self._trigger_change()

class FolderMonitor:
    def __init__(self, folder: Path, audio_extensions: set, change_callback: Callable):
        self.folder = folder
        self.observer = Observer()
        self.handler = MusicFolderHandler(audio_extensions, change_callback)
    
    def start(self):
        \"\"\"Start monitoring the folder\"\"\"
        self.observer.schedule(self.handler, str(self.folder), recursive=True)
        self.observer.start()
    
    def stop(self):
        \"\"\"Stop monitoring\"\"\"
        self.observer.stop()
        self.observer.join()
"""

OLLAMA_CLIENT_PY = """\"\"\"Ollama LLM integration for playlist generation\"\"\"

import requests
import json
from typing import List, Dict

class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
    
    def generate_playlist(self, user_request: str, tracks: List[Dict], max_tracks: int = 1000) -> Dict:
        \"\"\"
        Ask Ollama to select tracks based on user request
        
        Args:
            user_request: Natural language description of desired playlist
            tracks: List of track dictionaries from database
            max_tracks: Maximum number of tracks to include in context
            
        Returns:
            Dict with 'playlist' (list of selected tracks) and optionally 'reasoning'
        \"\"\"
        
        # If library is huge, sample it (or implement smarter filtering)
        if len(tracks) > max_tracks:
            tracks = tracks[:max_tracks]  # Simple truncation for now
        
        # Build the prompt
        prompt = self._build_prompt(user_request, tracks)
        
        # Call Ollama
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7
                }
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.text}")
        
        result = response.json()
        return self._parse_response(result['response'])
    
    def _build_prompt(self, user_request: str, tracks: List[Dict]) -> str:
        \"\"\"Build the prompt for Ollama\"\"\"
        
        tracks_json = json.dumps(tracks, indent=2)
        
        prompt = f\"\"\"You are a music expert creating playlists. Given a library of tracks and a user request, select tracks that match the request.

User request: "{user_request}"

Available tracks:
{tracks_json}

Respond ONLY with a JSON object in this exact format:
{{
  "playlist": [
    {{"title": "Song Title", "artist": "Artist Name"}},
    ...
  ],
  "reasoning": "Brief explanation of your selections"
}}

Rules:
- Select 10-20 tracks that best match the request
- Consider genre, mood, energy, era
- Order tracks for good flow
- If the request mentions duration, try to match it
- NO preamble, NO markdown, ONLY the JSON object
\"\"\"
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict:
        \"\"\"Parse Ollama's JSON response\"\"\"
        # Strip any markdown code fences if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Ollama response: {e}\\nResponse was: {response_text}")
"""

GENERATOR_PY = """\"\"\"M3U playlist file generation\"\"\"

from pathlib import Path
from typing import List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Track
from datetime import datetime

class PlaylistGenerator:
    def __init__(self, output_folder: Path):
        self.output_folder = output_folder
        self.output_folder.mkdir(parents=True, exist_ok=True)
    
    def create_m3u(self, tracks: List[Track], playlist_name: str = None) -> Path:
        \"\"\"
        Create an M3U playlist file
        
        Args:
            tracks: List of Track objects to include
            playlist_name: Optional name for playlist, otherwise uses timestamp
            
        Returns:
            Path to created M3U file
        \"\"\"
        if not playlist_name:
            playlist_name = f"playlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Sanitize filename
        safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).strip()
        m3u_path = self.output_folder / f"{safe_name}.m3u"
        
        with open(m3u_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\\n")
            
            for track in tracks:
                # Write extended info line
                duration = track.duration or -1
                f.write(f"#EXTINF:{duration},{track.artist} - {track.title}\\n")
                
                # Write file path
                f.write(f"{track.filepath}\\n")
        
        return m3u_path
"""

CHAT_WINDOW_PY = """\"\"\"Tkinter chat interface\"\"\"

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from pathlib import Path
from typing import Callable, Optional

class ChatWindow:
    def __init__(self, 
                 on_send_message: Callable[[str], None],
                 on_rescan: Callable[[], None],
                 on_change_folder: Callable[[Path], None]):
        \"\"\"
        Args:
            on_send_message: Callback when user sends a message
            on_rescan: Callback when user clicks rescan button
            on_change_folder: Callback when user selects new music folder
        \"\"\"
        self.on_send_message = on_send_message
        self.on_rescan = on_rescan
        self.on_change_folder = on_change_folder
        
        self.root = tk.Tk()
        self.root.title("Music Playlist Generator")
        self.root.geometry("800x600")
        
        self._setup_ui()
    
    def _setup_ui(self):
        \"\"\"Create the UI layout\"\"\"
        
        # Top toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        self.folder_label = ttk.Label(toolbar, text="Music Folder: Not set")
        self.folder_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="Change Folder", command=self._change_folder).pack(side=tk.LEFT, padx=5)
        
        self.rescan_btn = ttk.Button(toolbar, text="Rescan Library", command=self._rescan, state=tk.DISABLED)
        self.rescan_btn.pack(side=tk.LEFT, padx=5)
        
        self.track_count_label = ttk.Label(toolbar, text="Tracks: 0")
        self.track_count_label.pack(side=tk.RIGHT, padx=5)
        
        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(
            self.root, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=("Arial", 10)
        )
        self.chat_display.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure tags for styling
        self.chat_display.tag_config("user", foreground="blue", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("assistant", foreground="green")
        self.chat_display.tag_config("system", foreground="gray", font=("Arial", 9, "italic"))
        
        # Input area
        input_frame = ttk.Frame(self.root)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.input_field = ttk.Entry(input_frame, font=("Arial", 10))
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_field.bind("<Return>", lambda e: self._send_message())
        
        self.send_btn = ttk.Button(input_frame, text="Send", command=self._send_message)
        self.send_btn.pack(side=tk.RIGHT)
    
    def _change_folder(self):
        \"\"\"Let user select a new music folder\"\"\"
        folder = filedialog.askdirectory(title="Select Music Folder")
        if folder:
            self.on_change_folder(Path(folder))
    
    def _rescan(self):
        \"\"\"Trigger library rescan\"\"\"
        self.on_rescan()
    
    def _send_message(self):
        \"\"\"Send user message\"\"\"
        message = self.input_field.get().strip()
        if message:
            self.input_field.delete(0, tk.END)
            self.on_send_message(message)
    
    def add_message(self, sender: str, message: str):
        \"\"\"Add a message to the chat display\"\"\"
        self.chat_display.config(state=tk.NORMAL)
        
        tag = "system"
        if sender == "You":
            tag = "user"
        elif sender == "Assistant":
            tag = "assistant"
        
        self.chat_display.insert(tk.END, f"{sender}: ", tag)
        self.chat_display.insert(tk.END, f"{message}\\n\\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def update_folder_label(self, folder: Path):
        \"\"\"Update the folder display\"\"\"
        self.folder_label.config(text=f"Music Folder: {folder}")
        self.rescan_btn.config(state=tk.NORMAL)
    
    def update_track_count(self, count: int):
        \"\"\"Update the track count display\"\"\"
        self.track_count_label.config(text=f"Tracks: {count}")
    
    def show_rescan_notification(self):
        \"\"\"Highlight the rescan button\"\"\"
        self.rescan_btn.config(text="⚠ Rescan Library (changes detected)")
    
    def clear_rescan_notification(self):
        \"\"\"Clear rescan notification\"\"\"
        self.rescan_btn.config(text="Rescan Library")
    
    def run(self):
        \"\"\"Start the UI event loop\"\"\"
        self.root.mainloop()
"""

MAIN_PY = """\"\"\"Music Playlist Generator - Main Application\"\"\"

import sys
from pathlib import Path
import config
from database.db_manager import MusicDatabase
from scanner.music_scanner import MusicScanner
from scanner.folder_monitor import FolderMonitor
from llm.ollama_client import OllamaClient
from playlist.generator import PlaylistGenerator
from ui.chat_window import ChatWindow
import threading

class MusicPlaylistApp:
    def __init__(self):
        self.db = MusicDatabase(config.DB_PATH)
        self.scanner = MusicScanner(progress_callback=self._scan_progress)
        self.llm = OllamaClient(config.OLLAMA_BASE_URL, config.OLLAMA_MODEL)
        self.playlist_gen = PlaylistGenerator(config.PLAYLIST_OUTPUT)
        
        self.current_folder = config.MUSIC_FOLDER
        self.folder_monitor = None
        
        # Create UI
        self.ui = ChatWindow(
            on_send_message=self._handle_user_message,
            on_rescan=self._rescan_library,
            on_change_folder=self._change_music_folder
        )
        
        # Initialize
        self._startup()
    
    def _startup(self):
        \"\"\"Initial startup - scan library if needed\"\"\"
        track_count = self.db.get_track_count()
        
        if track_count == 0:
            self.ui.add_message("System", "Welcome! Please select your music folder to get started.")
        else:
            self.ui.add_message("System", f"Library loaded: {track_count} tracks")
            self.ui.update_track_count(track_count)
            self.ui.update_folder_label(self.current_folder)
            self._start_folder_monitor()
    
    def _change_music_folder(self, folder: Path):
        \"\"\"Handle folder change\"\"\"
        self.current_folder = folder
        self.ui.update_folder_label(folder)
        self.ui.add_message("System", f"Scanning {folder}...")
        
        # Stop existing monitor if any
        if self.folder_monitor:
            self.folder_monitor.stop()
        
        # Scan in background thread
        thread = threading.Thread(target=self._scan_library, daemon=True)
        thread.start()
    
    def _scan_library(self):
        \"\"\"Scan the music library (runs in background thread)\"\"\"
        tracks = self.scanner.scan_folder(self.current_folder, config.AUDIO_EXTENSIONS)
        
        # Update database
        for track in tracks:
            self.db.add_track(track)
        
        count = self.db.get_track_count()
        self.ui.add_message("System", f"Scan complete! Found {count} tracks.")
        self.ui.update_track_count(count)
        
        # Start monitoring
        self._start_folder_monitor()
    
    def _scan_progress(self, current: int, total: int, filepath: str):
        \"\"\"Callback during scan\"\"\"
        if current % 100 == 0:  # Update every 100 files
            self.ui.add_message("System", f"Scanning... {current}/{total}")
    
    def _rescan_library(self):
        \"\"\"Rescan the library\"\"\"
        self.ui.add_message("System", "Rescanning library...")
        self.ui.clear_rescan_notification()
        thread = threading.Thread(target=self._scan_library, daemon=True)
        thread.start()
    
    def _start_folder_monitor(self):
        \"\"\"Start monitoring the music folder for changes\"\"\"
        if self.folder_monitor:
            self.folder_monitor.stop()
        
        self.folder_monitor = FolderMonitor(
            self.current_folder,
            config.AUDIO_EXTENSIONS,
            self._on_folder_change
        )
        self.folder_monitor.start()
    
    def _on_folder_change(self):
        \"\"\"Called when folder changes detected\"\"\"
        self.ui.show_rescan_notification()
        self.ui.add_message("System", "Music folder changed. Click 'Rescan Library' to update.")
    
    def _handle_user_message(self, message: str):
        \"\"\"Process user's playlist request\"\"\"
        self.ui.add_message("You", message)
        
        # Get all tracks from database
        all_tracks = self.db.get_all_tracks()
        
        if not all_tracks:
            self.ui.add_message("Assistant", "No tracks in library. Please scan a music folder first.")
            return
        
        self.ui.add_message("System", "Thinking...")
        
        # Run LLM request in background
        thread = threading.Thread(
            target=self._generate_playlist,
            args=(message, all_tracks),
            daemon=True
        )
        thread.start()
    
    def _generate_playlist(self, request: str, all_tracks: list):
        \"\"\"Generate playlist using LLM (runs in background)\"\"\"
        try:
            # Convert tracks to dict format for LLM
            tracks_dict = [t.to_dict() for t in all_tracks]
            
            # Get LLM response
            response = self.llm.generate_playlist(request, tracks_dict)
            
            # Match LLM selections to actual tracks
            selected_tracks = []
            for selection in response.get('playlist', []):
                title = selection.get('title')
                artist = selection.get('artist')
                
                # Find matching track
                for track in all_tracks:
                    if track.title == title and track.artist == artist:
                        selected_tracks.append(track)
                        break
            
            if not selected_tracks:
                self.ui.add_message("Assistant", "Couldn't find matching tracks. Try a different request?")
                return
            
            # Generate M3U file
            playlist_path = self.playlist_gen.create_m3u(selected_tracks, f"playlist_{len(selected_tracks)}_tracks")
            
            # Show result
            reasoning = response.get('reasoning', 'No reasoning provided')
            message = f"Created playlist with {len(selected_tracks)} tracks!\\n\\n"
            message += f"Reasoning: {reasoning}\\n\\n"
            message += f"Saved to: {playlist_path}\\n\\n"
            message += "Tracks:\\n" + "\\n".join([f"- {t.artist} - {t.title}" for t in selected_tracks[:10]])
            
            if len(selected_tracks) > 10:
                message += f"\\n... and {len(selected_tracks) - 10} more"
            
            self.ui.add_message("Assistant", message)
            
        except Exception as e:
            self.ui.add_message("Assistant", f"Error generating playlist: {str(e)}")
    
    def run(self):
        \"\"\"Start the application\"\"\"
        try:
            self.ui.run()
        finally:
            # Cleanup
            if self.folder_monitor:
                self.folder_monitor.stop()


if __name__ == "__main__":
    app = MusicPlaylistApp()
    app.run()
"""

# ============================================
# RUN THE BOOTSTRAP
# ============================================

if __name__ == "__main__":
    print("🎵 Music Playlist Generator - Bootstrap Script")
    print("=" * 50)
    create_project_structure()