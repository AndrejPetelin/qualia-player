"""Music Playlist Generator - Main Application"""

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
        """Initial startup - scan library if needed"""
        track_count = self.db.get_track_count()
        
        if track_count == 0:
            self.ui.add_message("System", "Welcome! Please select your music folder to get started.")
        else:
            self.ui.add_message("System", f"Library loaded: {track_count} tracks")
            self.ui.update_track_count(track_count)
            self.ui.update_folder_label(self.current_folder)
            self._start_folder_monitor()
    
    def _change_music_folder(self, folder: Path):
        """Handle folder change"""
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
        """Scan the music library (runs in background thread)"""
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
        """Start monitoring the music folder for changes"""
        if self.folder_monitor:
            self.folder_monitor.stop()
        
        self.folder_monitor = FolderMonitor(
            self.current_folder,
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
            
            # Generate M3U file
            playlist_path = self.playlist_gen.create_m3u(selected_tracks, f"playlist_{len(selected_tracks)}_tracks")
            
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
    app = MusicPlaylistApp()
    app.run()
