"""Music Playlist Generator - Main Application"""

import sys
import subprocess
import atexit
from pathlib import Path
from datetime import datetime
import config
from database.db_manager import MusicDatabase
from scanner.music_scanner import MusicScanner
from scanner.folder_monitor import FolderMonitor
from llm.ollama_client import OllamaClient
from playlist.generator import PlaylistGenerator
from ui.chat_window import ChatWindow
import threading
import time
import requests


def check_ollama():
    """Check if Ollama is running"""
    try:
        
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        
        if response.status_code == 200:
            print("✅ Ollama is running!")
            return True
        else:
            print(f"⚠️  Ollama responded but with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def stop_ollama():
    """Stop Ollama on exit (optional - might want to leave it running)"""
    # Usually better to leave Ollama running
    pass


class MusicPlaylistApp:
    def __init__(self):
        self.db = MusicDatabase(config.DB_PATH)
        self.scanner = MusicScanner(progress_callback=self._scan_progress)
        self.llm = OllamaClient(config.OLLAMA_BASE_URL, config.OLLAMA_MODEL)
        self.playlist_gen = PlaylistGenerator(config.PLAYLIST_OUTPUT)
        
        # Load all configured music folders from database
        self.music_folders = self.db.get_music_folders()
        if not self.music_folders:
            # If no folders configured, use the default from config
            self.music_folders = [str(config.MUSIC_FOLDER)]
        
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
        """Initial startup - scan library if needed"""
        track_count = self.db.get_track_count()

    
        
        if track_count == 0:
            self.ui.add_message("System", "Welcome! Please select your music folder to get started.")
        else:
            self.ui.add_message("System", f"Library loaded: {track_count} tracks from {len(self.music_folders)} folder(s)")
            self.ui.update_track_count(track_count)
            # Show all configured folders
            folders_text = "\n".join([f"  • {f}" for f in self.music_folders])
            self.ui.update_folder_label(f"Monitoring {len(self.music_folders)} folder(s):\n{folders_text}")
            self._start_folder_monitor()
    
    
    def _change_music_folder(self, folder: Path):
        """Handle adding a new music folder"""
        folder_str = str(folder)
        
        # Add to database
        self.db.add_music_folder(folder_str)
        
        # Add to our list if not already there
        if folder_str not in self.music_folders:
            self.music_folders.append(folder_str)
        
        # Update UI
        folders_text = "\n".join([f"  • {f}" for f in self.music_folders])
        self.ui.update_folder_label(f"Monitoring {len(self.music_folders)} folder(s):\n{folders_text}")
        self.ui.add_message("System", f"Added folder: {folder}\nScanning...")
        
        # Scan just this new folder in background thread
        thread = threading.Thread(target=self._scan_single_folder, args=(folder,), daemon=True)
        thread.start()
    
    def _scan_single_folder(self, folder: Path):
        """Scan a single music folder (runs in background thread)"""
        tracks = self.scanner.scan_folder(folder, config.AUDIO_EXTENSIONS)
        
        # Update database
        for track in tracks:
            self.db.add_track(track)
        
        count = self.db.get_track_count()
        self.ui.add_message("System", f"Scan complete! Library now has {count} total tracks.")
        self.ui.update_track_count(count)
        
        # Restart monitoring for all folders
        self._start_folder_monitor()
    
    def _scan_library(self):
        """Scan ALL configured music folders (runs in background thread)"""
        total_scanned = 0
        
        for folder_str in self.music_folders:
            folder = Path(folder_str)
            if not folder.exists():
                self.ui.add_message("System", f"⚠️ Folder not found: {folder}")
                continue
            
            self.ui.add_message("System", f"Scanning {folder}...")
            tracks = self.scanner.scan_folder(folder, config.AUDIO_EXTENSIONS)
            
            # Update database
            for track in tracks:
                self.db.add_track(track)
            
            total_scanned += len(tracks)
        
        count = self.db.get_track_count()
        self.ui.add_message("System", f"Scan complete! Found {total_scanned} tracks across {len(self.music_folders)} folder(s). Total library: {count} tracks.")
        self.ui.update_track_count(count)
        
        # Start monitoring
        self._start_folder_monitor()
    
    def _scan_progress(self, current: int, total: int, filepath: str):
        """Callback during scan"""
        if current % 100 == 0:  # Update every 100 files
            self.ui.add_message("System", f"Scanning... {current}/{total}")
    
    def _rescan_library(self):
        """Rescan the library"""
        self.ui.add_message("System", "Rescanning library...")
        self.ui.clear_rescan_notification()
        thread = threading.Thread(target=self._scan_library, daemon=True)
        thread.start()
    
    def _start_folder_monitor(self):
        """Start monitoring all music folders for changes"""
        if self.folder_monitor:
            self.folder_monitor.stop()
        
        # For now, just monitor the first folder
        # TODO: Could create multiple monitors or a single monitor for all folders
        if self.music_folders:
            first_folder = Path(self.music_folders[0])
            self.folder_monitor = FolderMonitor(
                first_folder,
                config.AUDIO_EXTENSIONS,
                self._on_folder_change
            )
            self.folder_monitor.start()
    
    def _on_folder_change(self):
        """Called when folder changes detected"""
        self.ui.show_rescan_notification()
        self.ui.add_message("System", "Music folder changed. Click 'Rescan Library' to update.")
    
    def _handle_user_message(self, message: str):
        """Process user's playlist request"""
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
    
    # In main.py, find the _generate_playlist method and replace it with this:

    def _generate_playlist(self, request: str, all_tracks: list):
        """Generate playlist using LLM (runs in background)"""
        try:
            # Convert tracks to dict format for LLM
            tracks_dict = [t.to_dict() for t in all_tracks]
            
            # DEBUG: Show genre distribution
            genres = {}
            for t in all_tracks:
                g = t.genre or "Unknown"
                genres[g] = genres.get(g, 0) + 1
            
            self.ui.add_message("System", f"Library genres: {', '.join([f'{k} ({v})' for k, v in sorted(genres.items(), key=lambda x: -x[1])[:10]])}")
            
            # NEW DEBUG - just show what we're asking for
            self.ui.add_message("System", f"Asking Mistral to filter artists by music knowledge...")
            
            # Get LLM response (this now does TWO calls internally)
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
            
            # DEBUG: Show what was actually selected
            selected_genres = {}
            selected_artists = {}
            for t in selected_tracks:
                g = t.genre or "Unknown"
                selected_genres[g] = selected_genres.get(g, 0) + 1
                selected_artists[t.artist] = selected_artists.get(t.artist, 0) + 1
            
            # Create name with timestamp AND track count
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            playlist_path = self.playlist_gen.create_m3u(selected_tracks, f"playlist_{len(selected_tracks)}_tracks_{timestamp}")
            
            # Show result
            reasoning = response.get('reasoning', 'No reasoning provided')
            message = f"Created playlist with {len(selected_tracks)} tracks!\n\n"
            message += f"Reasoning: {reasoning}\n\n"
            message += f"Artists breakdown: {', '.join([f'{k} ({v})' for k, v in sorted(selected_artists.items(), key=lambda x: -x[1])])}\n\n"
            message += f"Selected genres: {', '.join([f'{k} ({v})' for k, v in sorted(selected_genres.items(), key=lambda x: -x[1])])}\n\n"
            message += f"Saved to: {playlist_path}\n\n"
            message += "Tracks:\n" + "\n".join([f"- {t.artist} - {t.title} [{t.genre or 'Unknown'}]" for t in selected_tracks[:15]])
            
            if len(selected_tracks) > 15:
                message += f"\n... and {len(selected_tracks) - 15} more"
            
            self.ui.add_message("Assistant", message)
            
        except Exception as e:
            import traceback
            self.ui.add_message("Assistant", f"Error generating playlist: {str(e)}\n\n{traceback.format_exc()}")
    
    def run(self):
        """Start the application"""
        try:
            self.ui.run()
        finally:
            # Cleanup
            if self.folder_monitor:
                self.folder_monitor.stop()


if __name__ == "__main__":

    
    # Just check, don't try to start
    if not check_ollama():
        print("\nPlease start Ollama manually with: ollama serve")
        print("Then run this program again.\n")
        sys.exit(1)
    
    app = MusicPlaylistApp()
    app.run()