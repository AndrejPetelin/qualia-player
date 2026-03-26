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
        matching_artists, artist_reasoning = self._get_genre_filtered_artists(user_request, tracks)
        print(f"⏱️  Mistral artist filter: {time.time() - t1:.1f}s")
        if not matching_artists:
            return {
                'playlist': [],
                'reasoning': "Mistral couldn't find artists matching that request in your library.",
                'artist_reasoning': artist_reasoning
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
                'reasoning': "Filters removed all tracks. Try a different request or check your metadata.",
                'artist_reasoning': artist_reasoning
            }

       
        
        # Phase 3: If strict rules (one per album, chronological), skip Mistral proportions
        t3 = time.time()
        if track_filter.needs_python_enforcement():

            # Python already ordered/selected the tracks - just return them!
            # Return full track data (includes filepath, album, year, etc.)
            return {
                'playlist': filtered_tracks,
                'reasoning': f"Selected {len(filtered_tracks)} tracks with strict filtering (year/album/chronological)",
                'artist_reasoning': artist_reasoning
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
            'reasoning': f"Selected {len(matched)} tracks from {len(selections)} artists with filtering applied",
            'artist_reasoning': artist_reasoning
        }
    
    def _get_genre_filtered_artists(self, user_request: str, tracks: List[Dict]) -> tuple[Set[str], Set[str]]:
        """Ask Mistral which artists match the request using injected metadata."""
        
        # Build catalog with GENRE hints to prevent "Barracuda" type mistakes
        artist_catalog = defaultdict(lambda: {'genres': set(), 'samples': []})
        for track in tracks:
            artist = track['artist']
            if track.get('genre'):
                artist_catalog[artist]['genres'].add(track['genre'])
            if len(artist_catalog[artist]['samples']) < 2:
                artist_catalog[artist]['samples'].append(track['title'])
        
        catalog_lines = []
        for artist, data in sorted(artist_catalog.items()):
            genres = ", ".join(list(data['genres'])[:3])
            samples = ", ".join(data['samples'])
            catalog_lines.append(f"- {artist} [Genres: {genres}] (Samples: {samples})")
        
        catalog_text = '\n'.join(catalog_lines)
        print(f"⏱️  catalog lines: {catalog_text}")
        
        prompt = f"""You are a music expert. User wants: "{user_request}"

    Available library artists with their metadata:
    {catalog_text}

    CRITICAL: Match ONLY artists who have music strictly fitting the mood/genre of "{user_request}".
    - If "ballads" are requested, avoid artists/tracks marked as "High Energy" or "Hard Rock" unless they are known for slow songs.
    - Be inclusive, but prioritize the primary vibe requested.

    Respond ONLY with JSON:
    {{
      "matching_artists": ["Artist 1", "Artist 2"],
      "reasoning": "Explain your logic based on the provided genres and samples."
    }}"""
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
            reasoning = parsed.get('reasoning', 'No reasoning provided')
            
            # DEBUG: Print what Mistral filtered to AND why
            print(f"\n🎵 Mistral's artist filter:")
            print(f"   Artists: {sorted(matching)}")
            print(f"   Reasoning: {reasoning}\n")
            
            return matching, reasoning
            
        except Exception as e:
            print(f"Error in genre filtering: {e}")
            # Fallback: return empty set and error message
            return set(), f"Error: {str(e)}"
    
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
        """Ask Mistral to decide proportions with strict VARIETY rules."""
        
        artists_list = '\n'.join([f"- {artist}" for artist in sorted(artists)])
        
        # Calculate variety constraints dynamically
        min_artists = max(5, target_tracks // 2)
        max_per_artist = 2 if target_tracks <= 20 else 3

        prompt = f"""You are creating a "{user_request}" playlist.
    Target: {target_tracks} tracks.

    Available matching artists:
    {artists_list}

    STRICT SELECTION RULES:
    1. VARIETY: You MUST select at least {min_artists} different artists.
    2. LIMIT: Maximum {max_per_artist} tracks per artist. Do not cluster!
    3. Total must be approximately {target_tracks}.
    4. Prioritize artists mentioned in: "{user_request}".

    Respond ONLY with JSON:
    {{
      "selections": [
        {{"artist": "Name", "num_tracks": 1, "reasoning": "Fits the mood"}},
        ...
      ]
    }}
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
                matched.append(track)
        
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