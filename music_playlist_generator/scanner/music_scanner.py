"""Music library scanner with three-pass metadata extraction"""

from pathlib import Path
from typing import List, Callable, Optional
from database.models import Track
from scanner.smart_scanner import SmartScanner

class MusicScanner:
    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Args:
            progress_callback: Function called with (current, total, filepath) during scan
        """
        self.progress_callback = progress_callback
        self.smart_scanner = SmartScanner()
    
    def scan_folder(self, folder: Path, extensions: set) -> List[Track]:
        """Recursively scan folder using three-pass strategy"""
        
        # Collect all audio files
        audio_files = []
        print("\nScanning for audio files...")
        for ext in extensions:
            audio_files.extend(folder.rglob(f"*{ext}"))
        
        total = len(audio_files)
        print(f"Found {total} audio files\n")
        
        # Use three-pass scanning
        tracks, failed = self.smart_scanner.scan_with_three_passes(
            audio_files, 
            progress_callback=self.progress_callback
        )
        
        # Generate failure report if needed
        if failed:
            self._generate_failure_report(failed)
        else:
            print("\n🎉 All files successfully parsed!")
        
        return tracks
    
    def _generate_failure_report(self, failed: List[dict]):
        """Generate a report of files that couldn't be parsed"""
        
        report_path = Path.home() / "qualia_failed_files.txt"
        
        print("\n" + "="*80)
        print("GENERATING FAILURE REPORT")
        print("="*80)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("QUALIA PLAYER - FAILED FILE REPORT\n")
            f.write("="*80 + "\n\n")
            f.write(f"Total files that couldn't be parsed: {len(failed)}\n\n")
            f.write("These files have incomplete or garbage metadata.\n")
            f.write("Mistral tried to parse them and failed.\n\n")
            f.write("RECOMMENDATIONS:\n")
            f.write("  1. Fix folder names (Artist/Year - Album/tracks)\n")
            f.write("  2. Remove uploader signatures (By SmSma, [TeamRip], etc.)\n")
            f.write("  3. Re-tag with MusicBrainz Picard\n")
            f.write("  4. Remove website spam from tags (MyEgy.CoM, etc.)\n\n")
            f.write("What.CD didn't die for this.\n\n")
            f.write("="*80 + "\n\n")
            
            for entry in failed:
                filepath = entry['filepath']
                warnings = entry.get('warnings', {})
                
                f.write(f"FILE: {filepath}\n")
                f.write(f"  Folder: {filepath.parent}\n")
                
                if warnings:
                    f.write("  Warnings:\n")
                    for field, warning in warnings.items():
                        f.write(f"    - {warning}\n")
                
                tag_data = entry.get('tag_data', {})
                f.write(f"  Tags: artist='{tag_data.get('artist')}', ")
                f.write(f"album='{tag_data.get('album')}', ")
                f.write(f"title='{tag_data.get('title')}'\n")
                f.write("\n")
        
        print(f"\n❌ {len(failed)} files failed - report saved to: {report_path}")
        print("="*80)
