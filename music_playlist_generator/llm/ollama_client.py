# llm/ollama_client.py - REPLACE ENTIRE FILE

"""Ollama LLM integration - uses Mistral's music knowledge instead of metadata tags"""

import requests
import json
from typing import List, Dict, Set
from collections import defaultdict
from .track_filters import TrackFilter
import time

class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
    
    def generate_playlist(self, user_request: str, tracks: List[Dict]) -> Dict:
        """
        Hybrid approach with track filtering:
        1. Ask Mistral which artists match
        2. PYTHON filters tracks by year/album/live/etc
        3. Ask Mistral to pick proportions (or skip if strict rules)
        4. Match to actual tracks
        """
        print("Hello???")
        start = time.time()
        # Phase 1: Let Mistral filter artists by music knowledge
        t1 = time.time()
        matching_artists = self._get_genre_filtered_artists(user_request, tracks)
        print(f"⏱️  Mistral artist filter: {time.time() - t1:.1f}s")
        if not matching_artists:
            return {
                'playlist': [],
                'reasoning': "Mistral couldn't find artists matching that request in your library."
            }
        
        # Filter to only tracks from matching artists
        artist_filtered_tracks = [
            t for t in tracks 
            if t.get('artist') in matching_artists
        ]
        
        
        

        # Phase 2: Apply Python track filters (year, live, album, etc.)
        t2 = time.time()
        track_filter = TrackFilter(user_request)
        filtered_tracks = track_filter.apply(artist_filtered_tracks)
        
        print(f"⏱️  Python filtering: {time.time() - t2:.1f}s")

        if not filtered_tracks:
            return {
                'playlist': [],
                'reasoning': "Filters removed all tracks. Try a different request or check your metadata."
            }

       
        
        # Phase 3: If strict rules (one per album, chronological), skip Mistral proportions
        t3 = time.time()
        if track_filter.needs_python_enforcement():

            # Python already ordered/selected the tracks - just return them!
            matched = []
            for track in filtered_tracks:
                matched.append({
                    'artist': track['artist'],
                    'title': track['title'],
                    'album': track['album']
                })

            for track in matched:
                print(f"⏱️  matched track: {track}")
            # Return full track data (includes filepath, album, year, etc.)
            return {
                'playlist': matched,
                'reasoning': f"Selected {len(filtered_tracks)} tracks with strict filtering (year/album/chronological)"
            }
        
        # Phase 3b: Otherwise, let Mistral pick proportions from filtered tracks
        target_tracks = self._extract_target_duration(user_request)
        
        # Build artist list from filtered tracks
        filtered_artists = list(set(t['artist'] for t in filtered_tracks))
        selections = self._get_artist_selections(user_request, filtered_artists, target_tracks)
        print(f"⏱️  Mistral proportions: {time.time() - t3:.1f}s")
        # Phase 4: Match to filtered tracks
        t4 = time.time()
        matched = self._match_to_tracks(selections, filtered_tracks)
        print(f"⏱️  Match to tracks: {time.time() - t3:.1f}s")

        print(f"⏱️  TOTAL: {time.time() - start:.1f}s")
    
        return {
            'playlist': matched,
            'reasoning': f"Selected {len(matched)} tracks from {len(selections)} artists with filtering applied"
        }
    
    def _get_genre_filtered_artists(self, user_request: str, tracks: List[Dict]) -> Set[str]:
        """Ask Mistral which artists match the request using its music knowledge"""
        
        # Build artist catalog with sample track names (helps Mistral recognize artists)
        artist_catalog = defaultdict(list)
        for track in tracks:
            artist = track['artist']
            if len(artist_catalog[artist]) < 3:  # Keep 3 sample tracks per artist
                artist_catalog[artist].append(track['title'])
        
        # Format for Mistral - keep it concise
        catalog_lines = []
        for artist, samples in sorted(artist_catalog.items()):
            catalog_lines.append(f"- {artist} (sample tracks: {', '.join(samples)})")
        
        catalog_text = '\n'.join(catalog_lines)
        
        # ============================================
        # THIS IS THE PROMPT - REPLACE THIS WHOLE SECTION:
        # ============================================
        
        prompt = f"""You are a music expert. The user wants: "{user_request}"

Here are the available artists in their music library with sample track names:
{catalog_text}

Based on YOUR MUSIC KNOWLEDGE, which artists match this request?

MATCHING RULES:

For GENRE requests:
- Match both EXACT genre and CLOSELY RELATED genres
- "prog rock" should include: classic prog (Yes, Genesis, King Crimson), art rock (Pink Floyd), and prog-adjacent artists
- "prog metal" should include: progressive metal (Dream Theater, Queensryche), prog-metal fusion (Tool), and metal bands with significant prog elements
- "hard rock" should include: classic hard rock (Deep Purple, Whitesnake), hard rock/heavy metal crossover
- Be INCLUSIVE rather than pedantic - if a band is commonly associated with the genre, include them

For ATTRIBUTE requests (like "female singers", "instrumental", "80s"):
- Include ALL artists that match, even if it's just one member or some tracks
- "female singers" = ANY band with female vocals (Roxette, Heart, Halestorm, Amy Winehouse, Aretha Franklin, Ann Wilson, etc.)
- "instrumental" = ANY artist with instrumental tracks

For SPECIFIC ARTIST requests:
- Always include named artists regardless of genre
- CRITICAL: If user says "ONLY [artist]", "just [artist]", "no other artists", or similar:
  → ONLY include that specific artist, DO NOT include related/similar artists
  → Example: "only Whitesnake" → ["Whitesnake"] (NOT Deep Purple, even though Coverdale was in both)
  → Example: "just Dream Theater, no other bands" → ["Dream Theater"] only

EXAMPLES:
- "prog rock" → Pink Floyd (YES - art rock/psychedelic prog), Dream Theater (NO - that's prog metal)
- "prog metal" → Dream Theater (YES), Avenged Sevenfold (YES - significant prog elements)  
- "female singers" → Roxette (YES), Heart (YES), Halestorm (YES), Amy Winehouse (YES), Aretha Franklin (YES)
- "only Whitesnake" → Whitesnake (YES), Deep Purple (NO - user said ONLY Whitesnake)

Respond ONLY with JSON:
{{
  "matching_artists": ["Artist 1", "Artist 2", "Artist 3"]
}}

NO explanations, NO preamble, NO markdown, ONLY the JSON object.
"""
        # ============================================
        # END OF PROMPT - rest of the method stays the same:
        # ============================================
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3  # Lower temp for more consistent filtering
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.text}")
            
            result = response.json()
            parsed = self._parse_response(result['response'])
            matching = set(parsed.get('matching_artists', []))
            
            # DEBUG: Print what Mistral filtered to
            print(f"\n🎵 DEBUG - Mistral filtered to these artists: {sorted(matching)}\n")
            
            return matching
            
        except Exception as e:
            print(f"Error in genre filtering: {e}")
            # Fallback: return empty set
            return set()
    
    def _extract_target_duration(self, user_request: str) -> int:
        """Extract target number of tracks from request"""
        request_lower = user_request.lower()
        
        if '3 hour' in request_lower or 'three hour' in request_lower:
            return 45
        elif '2 hour' in request_lower or 'two hour' in request_lower:
            return 30
        elif '1 hour' in request_lower or 'one hour' in request_lower:
            return 15
        elif '45 min' in request_lower or 'forty' in request_lower:
            return 11
        elif '30 min' in request_lower or 'thirty' in request_lower:
            return 8
        else:
            return 15  # Default ~1 hour
    
    def _get_artist_selections(self, user_request: str, artists: List[str], target_tracks: int) -> List[Dict]:
        """Ask Mistral to decide how many tracks from each artist"""
        
        artists_list = '\n'.join([f"- {artist}" for artist in sorted(artists)])
        
        prompt = f"""You are creating a playlist. The user wants: "{user_request}"

Available artists (already filtered to match the request):
{artists_list}

Target: approximately {target_tracks} tracks total

Your job: Decide how many tracks from each artist for good variety and flow.

Rules:
1. ONLY select from artists listed above
2. Total should be around {target_tracks} tracks (can be slightly over/under)
3. Vary the distribution - don't give everyone equal amounts
4. If a specific artist was mentioned, prioritize them
5. Consider variety - spread across multiple artists

Respond ONLY with JSON:
{{
  "selections": [
    {{"artist": "Artist Name", "num_tracks": 5}},
    {{"artist": "Another Artist", "num_tracks": 3}},
    ...
  ]
}}

NO preamble, NO markdown, NO explanations, ONLY the JSON object.
"""
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.text}")
            
            result = response.json()
            parsed = self._parse_response(result['response'])
            
            return parsed.get('selections', [])
            
        except Exception as e:
            print(f"Error in artist selection: {e}")
            # Fallback: distribute evenly
            tracks_per_artist = max(1, target_tracks // len(artists))
            return [{"artist": a, "num_tracks": tracks_per_artist} for a in artists[:target_tracks]]
    
    def _match_to_tracks(self, selections: List[Dict], library: List[Dict]) -> List[Dict]:
        """Match artist selections to actual tracks"""
        
        import random
        
        matched = []
        
        for selection in selections:
            artist_name = selection.get('artist', '')
            num_tracks = selection.get('num_tracks', 1)
            
            # Find all tracks by this artist (fuzzy match - normalize artist names)
            artist_name_normalized = artist_name.lower().strip()
            
            artist_tracks = [
                t for t in library 
                if t.get('artist', '').lower().strip() == artist_name_normalized
            ]
            
            # Randomize the track order, then take num_tracks
            random.shuffle(artist_tracks)
            selected = artist_tracks[:num_tracks]
            
            # Return the FULL track data (includes filepath, album, year, genre, etc.)
            # This ensures we get the exact track that was filtered, not a different version
            for track in selected:
                matched.append({
                    'artist': track['artist'],
                    'title': track['title'],
                    'album': track['album']
                })
        
        return matched
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse Ollama's JSON response"""
        cleaned = response_text.strip()
        
        # Remove markdown code fences if present
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
        
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Try to extract JSON object from the response
            import re
            # Look for {  ...  } with proper nesting
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            # If still failing, print debug info
            print(f"\n❌ JSON Parse Error:")
            print(f"Full response: {response_text}")
            print(f"Cleaned: {cleaned}")
            
            # Last resort - try to build the JSON manually if it looks like just an array
            if cleaned.startswith('["') or cleaned.startswith("['"):
                try:
                    return {"matching_artists": json.loads(cleaned)}
                except:
                    pass
            
            raise Exception(f"Failed to parse JSON: {e}\nResponse: {response_text[:500]}")