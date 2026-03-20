"""Configuration settings for Music Playlist Generator"""

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
