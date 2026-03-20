"""M3U playlist file generation"""

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
        """
        Create an M3U playlist file
        
        Args:
            tracks: List of Track objects to include
            playlist_name: Optional name for playlist, otherwise uses timestamp
            
        Returns:
            Path to created M3U file
        """
        if not playlist_name:
            playlist_name = f"playlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Sanitize filename
        safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).strip()
        m3u_path = self.output_folder / f"{safe_name}.m3u"
        
        with open(m3u_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            
            for track in tracks:
                # Write extended info line
                duration = track.duration or -1
                f.write(f"#EXTINF:{duration},{track.artist} - {track.title}\n")
                
                # Write file path
                f.write(f"{track.filepath}\n")
        
        return m3u_path
