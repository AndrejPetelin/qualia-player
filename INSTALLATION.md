# Three-Pass Scanner Installation

## Files to Replace

1. **scanner/smart_scanner.py** - Complete rewrite with three-pass logic
2. **scanner/music_scanner.py** - Updated to use three-pass scanning

## What Changed

### Pass 1: Folder Structure (Fast)
- Parses folder names for artist/album/year
- Detects CD subfolders (CD1, CD2)
- Detects format subfolders (mp3, flac)
- Detects collection roots ("Glasba", "Music") by counting subfolders
- Parses "Artist - Album" patterns
- SUCCESS: Track added to database
- FAIL: Move to Pass 2

### Pass 2: ID3 Tags (Medium)
- Reads ID3 tags for Pass 1 failures
- Checks for garbage metadata (URLs, spam)
- Merges path + tag data intelligently
- SUCCESS: Track added to database
- FAIL: Move to Pass 3

### Pass 3: Mistral LLM (Slow)
- Asks Mistral to parse problematic filenames
- Only runs on files that failed Pass 1 AND Pass 2
- Examples: "Jeff Beck Emotion And Commotion 201o By SmSma"
- SUCCESS: Track added to database
- FAIL: Written to failure report

## Garbage Detection (Conservative)

Only flags OBVIOUS spam:
- Website URLs (.com, .net, MyEgy.CoM)
- Uploader signatures ("By SmSma" - capital B only!)
- Identical values in all fields

Does NOT flag:
- [bonus track], [remastered], [live]
- W.A.S.P., R.E.M. (short acronyms)
- "Obscured by Clouds" ("by" is lowercase)
- Xavlegbmaofffassssitimiwoamndutroabcwapwaeiippohfffx (yes, real band)

## Output

1. **Console**: Progress for each pass
2. **Database**: All successfully parsed tracks
3. **qualia_failed_files.txt**: Files that couldn't be parsed

## Installation

Copy the two files from /home/claude/ to your music_playlist_generator/scanner/ folder:

```bash
cp /home/claude/smart_scanner.py scanner/
cp /home/claude/music_scanner.py scanner/
```

Then delete old database and rescan:

```bash
python -c "from pathlib import Path; db = Path.home() / '.music_playlist_generator' / 'library.db'; db.unlink() if db.exists() else None; print('Deleted!')"
python main.py
```

## Expected Results

- Pass 1 should get ~80-90% of well-organized files
- Pass 2 should get ~5-10% more with tag fallback
- Pass 3 should rescue a few problematic cases
- Failure report should only contain truly broken files

Enjoy! 🎵
