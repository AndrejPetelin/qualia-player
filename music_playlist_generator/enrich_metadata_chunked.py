import sqlite3
import requests
import json
import re
import config

def enrich_library():
    # 1. Setup Logging
    log_file = open("enrichment_audit.log", "a", encoding="utf-8")
    
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    # 2. Get only tracks that are actually NULL
    cursor.execute("SELECT artist, album, title FROM tracks WHERE mood_tags IS NULL")
    missing_tracks = cursor.fetchall()

    # 3. Group them by Album so the AI has context
    album_groups = {}
    for artist, album, title in missing_tracks:
        key = (artist, album)
        if key not in album_groups:
            album_groups[key] = []
        album_groups[key].append(title)

    print(f"🚀 Found {len(missing_tracks)} missing tracks across {len(album_groups)} albums.")

    for (artist, album), titles in album_groups.items():
        # Chunk the titles (5 at a time is safest for Squashed Mistral)
        for i in range(0, len(titles), 5):
            chunk = titles[i:i+5]
            
            prompt = f"""You are a professional music librarian. 
Analyze these tracks from the album "{album}" by "{artist}". 

For each track, provide:
1. Tags: Choose 2-3 specific sub-genres or moods (e.g., Ballad, Hard Rock, Prog, Synth-Pop, Instrumental, Acoustic).
2. Tempo: Choose one [Slow, Mid, Fast].

            Output ONLY a JSON array for these specific tracks from '{album}' by '{artist}':
No chatter. No weights. No extra text.
Format: [{{"title": "track_name", "tags": ["tag1", "tag2"], "tempo": "Fast"}}]
Tracks to process: {", ".join(chunk)}"""

            log_file.write(f"\n--- PROMPT ({artist} - {album}) ---\n{prompt}\n")
            
            try:
                response = requests.post(
                    f"{config.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": config.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0,
                            "num_predict": 1000,
                            "stop": ["\n\n"]
                        }
                    },
                    timeout=120
                )
                
                raw_res = response.json().get('response', '').strip()
                log_file.write(f"RAW RESPONSE:\n{raw_res}\n")

                # Clean up trailing commas
                raw_res = re.sub(r',\s*([\]}])', r'\1', raw_res)
                data = json.loads(raw_res)
                tracks_to_process = []

                # CASE 1: It's already a list [{}, {}] - The Ideal Case
                if isinstance(data, list):
                    tracks_to_process = data

                # CASE 2: It's a dictionary { "key": [...] } or { "Track": {...} }
                elif isinstance(data, dict):
                    # Check if any value inside the dictionary is a list (The "data" wrapper case)
                    for value in data.values():
                        if isinstance(value, list):
                            tracks_to_process = value
                            break
                    
                    # If we didn't find a list, check if the values are dictionaries (The "Seize the Day" case)
                    if not tracks_to_process:
                        if any(isinstance(v, dict) for v in data.values()):
                            tracks_to_process = list(data.values())
                        else:
                            # It's just a single track object, wrap it
                            tracks_to_process = [data]

                for item in tracks_to_process:
                    ai_title = item.get('title')
                    tags = ", ".join(item.get('tags', ["mellow"]))
                    tempo = item.get('tempo', "Moderate")

                    if ai_title:
                        # 1. Try an exact match first
                        cursor.execute("""
                            UPDATE tracks 
                            SET mood_tags = ?, tempo = ? 
                            WHERE artist = ? AND album = ? AND title = ?
                        """, (tags, tempo, artist, album, ai_title))
                        
                        # 2. If that didn't work (rowcount is 0), try a 'LIKE' match
                        # This handles cases where the AI stripped track numbers or symbols
                        if cursor.rowcount == 0:
                            cursor.execute("""
                                UPDATE tracks 
                                SET mood_tags = ?, tempo = ? 
                                WHERE artist = ? AND album = ? AND title LIKE ?
                            """, (tags, tempo, artist, album, f"%{ai_title}%"))

                        if cursor.rowcount > 0:
                            log_file.write(f"    SUCCESS: Updated '{ai_title}'\n")
                        else:
                            log_file.write(f"    WARNING: No DB match found for title '{ai_title}'\n")
                
                # Commit after every chunk to ensure data is saved immediately
                conn.commit()
                log_file.write("STATUS: Success\n")
                print(f"    ✅ Updated {len(data)} tracks in {album}")

            except Exception as e:
                log_file.write(f"STATUS: FAILED - {str(e)}\n")
                print(f"    ❌ Error with {album}: {e}")

    log_file.close()
    conn.close()
    print("✨ Enrichment finished. Check enrichment_audit.log for details.")

if __name__ == "__main__":
    enrich_library()
