"""Filesystem monitoring for music library changes"""

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable
import time

class MusicFolderHandler(FileSystemEventHandler):
    def __init__(self, audio_extensions: set, change_callback: Callable):
        """
        Args:
            audio_extensions: Set of valid audio file extensions
            change_callback: Function to call when changes detected
        """
        self.audio_extensions = audio_extensions
        self.change_callback = change_callback
        self.last_change_time = 0
        self.debounce_seconds = 3
    
    def _is_audio_file(self, path: str) -> bool:
        return Path(path).suffix.lower() in self.audio_extensions
    
    def _trigger_change(self):
        """Debounced change notification"""
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
        """Start monitoring the folder"""
        self.observer.schedule(self.handler, str(self.folder), recursive=True)
        self.observer.start()
    
    def stop(self):
        """Stop monitoring"""
        self.observer.stop()
        self.observer.join()
