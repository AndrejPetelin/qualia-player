import sqlite3
import requests
import json
import time
# Importing your existing project files
import config 
from database.db_manager import MusicDatabase

def setup_additional_columns():
    """Uses your db_manager path to add the new metadata columns."""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    new_columns = [("mood_tags", "TEXT"), ("tempo", "TEXT")]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE tracks ADD COLUMN {col_name} {col_type}")
            print(f"✅ Added column: {col_name}")
        except sqlite3.OperationalError:
            print(f"ℹ️ Column {col_name} already exists.")
    
    conn.commit()
    conn.close()

def enrich_library():
    setup_additional_columns()
    
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    # Find unique albums that haven't been processed yet
    cursor.execute("SELECT DISTINCT artist, album FROM tracks WHERE mood_tags IS NULL")
    albums_to_process = cursor.fetchall()

    print(f"🚀 Processing {len(albums_to_process)} albums...")

    for artist, album in albums_to_process:
        if not album or not artist: continue
        
        # Get all track titles for this album to give the LLM context
        cursor.execute("SELECT title FROM tracks WHERE artist = ? AND album = ?", (artist, album))
        titles = [row[0] for row in cursor.fetchall()]
        
        print(f"  Tagging: {artist} - {album}...")

        prompt = f"""You are a professional music librarian. 
Analyze the album "{album}" by "{artist}". 
Tracks: {", ".join(titles)}

For each track, provide:
1. Tags: Choose 2-3 specific sub-genres or moods (e.g., Ballad, Hard Rock, Prog, Synth-Pop, Instrumental, Acoustic).
2. Tempo: Choose one [Slow, Mid, Fast].

Respond ONLY with a JSON list of objects:
[
  {{"title": "Track Name", "tags": ["Tag1", "Tag2"], "tempo": "Slow"}},
  ...
]"""

        try:
            response = requests.post(
                f"{config.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": config.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2} # Low temp for consistency
                },
                timeout=90
            )
            
            # Clean and parse JSON
            raw_res = response.json()['response'].strip()
            if "```json" in raw_res:
                raw_res = raw_res.split("```json")[1].split("```")[0]
            
            data = json.loads(raw_res)

            for item in data:
                tags_str = ", ".join(item.get('tags', []))
                cursor.execute("""
                    UPDATE tracks 
                    SET mood_tags = ?, tempo = ? 
                    WHERE artist = ? AND album = ? AND title = ?
                """, (tags_str, item.get('tempo'), artist, album, item.get('title')))
            
            conn.commit()
            
        except Exception as e:
            print(f"    ❌ Failed {album}: {e}")
            continue

    print("✨ Your library is now enriched with AI metadata!")
    conn.close()

if __name__ == "__main__":
    enrich_library()